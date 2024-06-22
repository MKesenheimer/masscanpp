#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import masscan
import random
import time
import json
import argparse
import requests
from multiprocessing import Process
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import TimeLimitExceeded
redis_broker = RedisBroker(host="127.0.0.1")
dramatiq.set_broker(redis_broker)

def timeout_process(process, timeout, ip, port):
    start_time = time.time()
    while process.is_alive():
        if time.time() - start_time > timeout:
            raise TimeLimitExceeded(f"Process timed out for IP: {ip}:{port}")
        time.sleep(0.1)  # Check every 100ms if the process is still running

# create child process to query public server information
@dramatiq.actor(max_age=3600000*24, time_limit=1000*60)
def status(ip, port):
    p = None
    print(f"[+] status: start {ip}:{port} start")
    try:
        p = Process(target=count_words, args=(ip, port, ))
        p.start()
        timeout_process(p, 10, ip, port)
        print(f"[+] status: end {ip}:{port} end {p}")
    except TimeLimitExceeded:
        print(f"[+] status: time {ip}:{port} {p}")
        if p:
            try:
                p.terminate()
            except:
                pass

@dramatiq.actor
def simple_status(ip, port):
    print(f"[+] status: start working on {ip}:{port}")
    count_words(ip, port)

# TODO: replace with function that checks fingerprint of open service
def count_words(ip, port):
    url = f"http://{ip}:{port}/"
    try:
        response = requests.get(url)
        count = len(response.text.split(" "))
        print(f"[+] There are {count} words at {url!r}.")
        # TODO: write out results
    except:
        print(f"[-] No response from {url!r}.")

def scan(port=80):
    A = list(range(1, 0xff))
    B = list(range(1, 0xff))
    random.shuffle(A)
    random.shuffle(B)
    ip_ranges = []
    for a in A:
        for b in B:
            ip_range = f"{a}.{b}.0.0/16"
            ip_ranges.append(ip_range)
    
    while True:
        # randomize IP ranges
        random.shuffle(ip_ranges)
        for ip_range in ip_ranges:
            print(f"[+] scanning {ip_range}")
            try:
                mas = masscan.PortScanner()
                mas.scan(ip_range, ports=str(port), arguments='--max-rate 262144')
                delay = 5000
                scan_result = json.loads(mas.scan_result)
                #print(scan_result['scan'])
                for ip in scan_result['scan']:
                    state = scan_result['scan'][ip][0]
                    print(f"[+] {ip} {state}")
                    if 'tcp' in state['proto'] and port == state['port'] and 'open' in state['status']:
                        print(f"[+] verifying status of {ip}:{port}")
                        simple_status.send_with_options(args=(ip, port, ), delay=delay)
                        #status.send_with_options(args=(ip, port, ), delay=delay)
                        delay += 5000
            except masscan.NetworkConnectionError:
                print(f"[-] {ip_range} masscan masscan.NetworkConnectionError")
                time.sleep(30)
        print('[+] done scanning')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='masscan the internet')
    parser.add_argument('-p', '--port', dest='port', help='Port to scan', type=int)
    args = parser.parse_args()
    try:
        scan(args.port)
    except KeyboardInterrupt:
        print('\nExitting...')
        sys.exit(1)