#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import masscan
import random
import time
import json
import argparse
import requests
import socket
from functools import reduce
from collections.abc import Callable
from multiprocessing import Process
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import TimeLimitExceeded, Shutdown, CurrentMessage
import signal
import logging

broker = RedisBroker(host="127.0.0.1")
broker.add_middleware(CurrentMessage())
dramatiq.set_broker(broker)
filename = "results.log"

class http:
    def count_words(host: str, port: int) -> bytes:
        url = f"http://{host}:{port}/"
        try:
            response = requests.get(url)
            count = len(response.text.split(" "))
            print(f"[+] there are {count} words at {url!r}.")
            # TODO: convert response.text to bytes
            return response.txt
        except Exception as e:
            print(f"[-] no response from {url!r}: {e}")
        return b''
    
    receive_response = count_words

class cola:
    def send_cola_request(socket, port: int):
        #payload = b'sRI 0'
        #payload = b'sRN FirmwareVersion'
        payload = b'sRN DeviceIdent'
        length = 1024
        if port == 2112:
            length = len(payload).to_bytes(4, 'big')
            crc = reduce(lambda x, y: x ^ y, payload, 0).to_bytes(1, 'big')
            header = b'\x02\x02\x02\x02'
            payload = header + length + payload + crc
        elif port == 2111:
            payload = b'\x02' + payload + b'\x03'
        print("[+] Sending payload:")
        print(payload)
        socket.sendall(payload)

    def receive_cola_response(socket, port: int) -> bytes:
        response = b''
        if port == 2112:
            header = socket.recv(4)
            length = socket.recv(4)
            length = int.from_bytes(length, byteorder='big')
            response = socket.recv(length)
            crc = socket.recv(1)
        elif port == 2111:
            response = socket.recv(1024)
        return response

    send_request = send_cola_request
    receive_response = receive_cola_response

class ip_ping:
    def __init__(self, type_name):
        self.receive_response = type_name.receive_response

    def send_and_receive(self, ip: str, port: int):
        response = self.receive_response(ip, port)
        if response != b'':
            with open(filename, 'a') as f:
                f.write(f"response from {ip} {port}:\n")
                f.write(str(response)+'\n')
            print(f"[+] response from {ip} {port}:")
            print(response)

class tcp_ping:
    def __init__(self, type_name):
        self.send_request = type_name.send_request
        self.receive_response = type_name.receive_response

    def send_and_receive(self, ip: str, port: int):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((ip, port))
        except Exception as e:
            print(f"[-] connection failed {ip}:{port}: {e}")
            return
        response = b''
        try:
            self.send_request(s, port)
            response = self.receive_response(s, port)
        except Exception as e:
            print(f"[-] verification failed for {ip}:{port} with exception: {e}")
        finally:
            s.close()
        if response != b'':
            with open(filename, 'a') as f:
                f.write(f"response from {ip} {port}:\n")
                f.write(str(response)+'\n')
            print(f"[+] response from {ip} {port}:")
            print(response)

@dramatiq.actor(max_age=3600000*24, time_limit=1000*60, notify_shutdown=True)
def status(ip, port):
    print(f"[+] verification status: start working on {ip}:{port}")
    try:
        ping_handler = None
        if port == 80:
            ping_handler = ip_ping(http)
        elif port == 2111 or port == 2112:
            ping_handler = tcp_ping(cola)
        ping_handler.send_and_receive(ip, port)
    except TimeLimitExceeded:
        print(f"[-] verification status: time limit exceeded {ip}:{port}")
    except Shutdown:
        print(f"[-] verification status: shutdown {ip}:{port}")
        # restart next time if process was shut down -> raise error to middleware
        raise
    except Exception:
        print(f"[+] verification status: general exception {ip}:{port}")
    print(f"[+] verification status: finished {ip}:{port}")

def scan(port=80):
    A = list(range(1, 0xff))
    B = list(range(1, 0xff))
    random.shuffle(A)
    random.shuffle(B)
    ip_ranges = []
    for a in A:
        for b in B:
            ip_range = f"{a}.{b}.0.0/16"
            #ip_range = "45.33.32.156"
            ip_ranges.append(ip_range)
    
    while True:
        # randomize IP ranges
        random.shuffle(ip_ranges)
        for ip_range in ip_ranges:
            print(f"[+] scanning {ip_range}")
            try:
                mas = masscan.PortScanner()
                mas.scan(ip_range, ports=str(port), arguments='--max-rate 1000000')
                delay = 1000
                scan_result = json.loads(mas.scan_result)
                #print(scan_result['scan'])
                for ip in scan_result['scan']:
                    state = scan_result['scan'][ip][0]
                    print(f"[+] {ip} {state}")
                    if 'tcp' in state['proto'] and port == state['port'] and 'open' in state['status']:
                        logging.info(f"found open port: {ip} {state}")
                        print(f"[+] verifying status of {ip}:{port}")
                        status.send_with_options(args=(ip, port, ), delay=delay)
                        delay += 1000
            except masscan.NetworkConnectionError:
                print(f"[-] {ip_range} masscan masscan.NetworkConnectionError")
                time.sleep(30)
        print('[+] done scanning')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='masscan the internet')
    parser.add_argument('-p', '--port', dest='port', help='Port to scan', type=int)
    args = parser.parse_args()

    logging.basicConfig(filename="scan.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

    try:
        scan(args.port)
    except KeyboardInterrupt:
        print('\nExitting...')
        sys.exit(1)