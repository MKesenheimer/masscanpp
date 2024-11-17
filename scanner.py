#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import masscan
import random
import time
import datetime
import json
import argparse
import socket
import ssl
from functools import reduce
from abc import ABC, abstractmethod
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import TimeLimitExceeded, Shutdown, CurrentMessage
import logging
from pymongo import MongoClient

# ignore TLS warnings
#ssl._create_default_https_context = ssl._create_unverified_context
ssl.SSLContext.verify_mode = property(lambda self: ssl.CERT_NONE, lambda self, newval: None)

broker = RedisBroker(host="127.0.0.1")
broker.add_middleware(CurrentMessage())
dramatiq.set_broker(broker)

results_prefix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_results"
mongo_connection_string = "mongodb://127.0.0.1/"

class protocol(ABC):
    @abstractmethod
    def send_and_receive():
        pass

class http(protocol):
    def send_and_receive(socket, ip: str, port: int) -> bytes:
        request = f"GET / HTTP/1.1\r\nHost:{ip}\r\nConnection: close\r\n\r\n".encode()
        socket.sendall(request)

        response = b""
        while True:
            chunk = socket.recv(4096)
            if len(chunk) == 0:
                # No more data received, quitting
                break
            response = response + chunk
        return response

class colaA(protocol):
    def send_and_receive(socket, ip: str, port: int) -> bytes:
        #payload = b'sRI 0'
        #payload = b'sRN FirmwareVersion'
        payload = b'sRN DeviceIdent'
        payload = b'\x02' + payload + b'\x03'
        print("[+] Sending payload:")
        print(payload)
        socket.sendall(payload)

        response = socket.recv(1024)
        return response

class colaB(protocol):
    def send_and_receive(socket, ip: str, port: int) -> bytes:
        #payload = b'sRI 0'
        #payload = b'sRN FirmwareVersion'
        payload = b'sRN DeviceIdent'
        length = 1024
        length = len(payload).to_bytes(4, 'big')
        crc = reduce(lambda x, y: x ^ y, payload, 0).to_bytes(1, 'big')
        header = b'\x02\x02\x02\x02'
        payload = header + length + payload + crc
        print("[+] Sending payload:")
        print(payload)
        socket.sendall(payload)

        header = socket.recv(4)
        length = socket.recv(4)
        length = int.from_bytes(length, byteorder='big')
        response = socket.recv(length)
        crc = socket.recv(1)
        return response

class ssh(protocol):
    def send_and_receive(socket, ip: str, port: int) -> bytes:
        response = socket.recv(1024)
        if b"SSH-" in response:
            return response
        else:
            return b""

class output:
    @staticmethod
    def create_object(ip: str, port: int, response: bytes):
        data = {}
        data['ip'] = ip
        data['port'] = port
        data['response'] = response.decode("utf-8")
        data['length'] = len(response)
        return data

    @staticmethod
    def write_response_to_file(ip: str, port: int, response: bytes):
        json_data = json.dumps(output.create_object(ip, port, response))
        filename = "./logs/" + results_prefix + f"_p{port}.json"
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(json_data)
            f.write('\n')

    @staticmethod
    def get_database():
        client = MongoClient(mongo_connection_string)
        # Create the database if none existent
        return client['db']

    @staticmethod
    def push_to_database(ip: str, port: int, response: bytes):
        dbname = output.get_database()
        collection_name = dbname["scan-results"]
        data = output.create_object(ip, port, response)
        try:
            collection_name.insert_one(data)
        except Exception as e:
            print(data)
            print(f"Error occured: {e}")

class connection_handler:
    def __init__(self, protocol):
        self.protocol_send_and_receive = protocol.send_and_receive

    def send_and_receive(self, ip: str, port: int):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        try:
            s.connect((ip, port))
        except Exception as e:
            print(f"[-] connection failed {ip}:{port}: {e}")
            return
        response = b''
        try:
            response = self.protocol_send_and_receive(s, ip, port)
        except socket.timeout as e:
            print(f"[-] verification failed for {ip}:{port} with socket timeout: {e}")
        except Exception as e:
            print(f"[-] verification failed for {ip}:{port} with exception: {e}")
        finally:
            s.close()
        if response != b'':
            #output.write_response_to_file(ip, port, response)
            output.push_to_database(ip, port, response)
            print(f"[+] response from {ip} {port}:")
            print(f"{response[0:60]}...")

    def secure_send_and_receive(self, ip: str, port: int):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)

        context = ssl.SSLContext(ssl_version=ssl.PROTOCOL_TLS) # ciphers="ADH-AES256-SHA"
        s_socket = context.wrap_socket(s, server_hostname=ip)

        try:
            s_socket.connect((ip, port))
        except Exception as e:
            print(f"[-] connection failed {ip}:{port}: {e}")
            return
        response = b''
        try:
            response = self.protocol_send_and_receive(s_socket, ip, port)
        except socket.timeout as e:
            print(f"[-] verification failed for {ip}:{port} with socket timeout: {e}")
        except Exception as e:
            print(f"[-] verification failed for {ip}:{port} with exception: {e}")
        finally:
            s_socket.close()
        if response != b'':
            #output.write_response_to_file(ip, port, response)
            output.push_to_database(ip, port, response)
            print(f"[+] response from {ip} {port}:")
            print(f"{response[0:60]}...")

def print_queue_len():
    for n in broker.get_declared_queues():
        queue_len = broker.do_qsize(n)
        print(f"[+] There are currently {queue_len} actors in queue dramatiq:{n}.")

def str_to_class(classname):
    return getattr(sys.modules[__name__], classname)

@dramatiq.actor(max_age=3600000*24, time_limit=1000*10, notify_shutdown=True)
def status(ip, port, protocol_str, secure):
    print(f"[+] verification status: start working on {ip}:{port}")
    try:
        connection = None
        if protocol_str == 'automatic':
            if port == 80 or port == 443:
                connection = connection_handler(http)
            elif port == 22:
                connection = connection_handler(ssh)
            elif port == 2111:
                connection = connection_handler(colaA)
            elif port == 2112:
                connection = connection_handler(colaB)
        else:
            connection = connection_handler(str_to_class(protocol_str))
        if secure:
            connection.secure_send_and_receive(ip, port)
        else:
            connection.send_and_receive(ip, port)
    except TimeLimitExceeded:
        print(f"[-] verification status: time limit exceeded {ip}:{port}")
    except Shutdown:
        print(f"[-] verification status: shutdown {ip}:{port}")
        # restart next time if process was shut down -> raise error to middleware
        raise
    except Exception as e:
        print(f"[-] verification status: general exception {ip}:{port}: {e}")
    print(f"[+] verification status: finished {ip}:{port}")
    print_queue_len()

def scan(port=80, protocol_str='automatic', secure=False):
    A = list(range(1, 0xff))
    B = list(range(1, 0xff))
    random.shuffle(A)
    random.shuffle(B)
    ip_ranges = []
    for a in A:
        for b in B:
            ip_range = f"{a}.{b}.0.0/16"
            ip_ranges.append(ip_range)
    
    # debug
    #ip_ranges = ['147.203.215.99']

    while True:
        # randomize IP ranges
        random.shuffle(ip_ranges)
        for ip_range in ip_ranges:
            print(f"[+] scanning {ip_range}")
            try:
                mas = masscan.PortScanner()
                mas.scan(ip_range, ports=str(port), arguments='--max-rate 1000000')
                delay = 100
                scan_result = json.loads(mas.scan_result)
                #print(scan_result['scan'])
                for ip in scan_result['scan']:
                    state = scan_result['scan'][ip][0]
                    print(f"[+] {ip} {state}")
                    if 'tcp' in state['proto'] and port == state['port'] and 'open' in state['status']:
                        logging.info(f"found open port: {ip} {state}")
                        print(f"[+] verifying status of {ip}:{port}")
                        status.send_with_options(args=(ip, port, protocol_str, secure), delay=delay)
                        #status.send_with_options(args=(ip, port, )) # without delay
                        print_queue_len()
                        delay += 1000
            except masscan.NetworkConnectionError:
                print(f"[-] {ip_range} masscan masscan.NetworkConnectionError")
                time.sleep(30)
        print('[+] done scanning')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='masscan the internet')
    parser.add_argument('-p', '--port', dest='port', help='Port to scan', type=int)
    parser.add_argument('--protocol', dest='protocol_str', help='Define the protocol (http, ssh, colaA, colaB, ...) to use to verify if the service is up.', type=str, default='automatic')
    parser.add_argument('--secure', dest='secure', action='store_true', help='Use a TLS secured connection to verify the status of the service (wraps the TCP traffic in a TLS tunnel).')
    args = parser.parse_args()

    logging.basicConfig(filename=f"./logs/scan-{args.port}.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

    try:
        scan(args.port, args.protocol_str, args.secure)
    except KeyboardInterrupt:
        print('\nExitting...')
        sys.exit(1)
