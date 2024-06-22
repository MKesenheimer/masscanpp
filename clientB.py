#!/usr/bin/env python3
# -*- conding: utf-8 -*-

import socket
import sys
import os
from binascii import hexlify, unhexlify
from functools import reduce

host = socket.gethostname()
port = 2112
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def send_and_receive(data: bytes):
    print("-> sending to device:")
    print(data)
    print()
    length = len(data).to_bytes(4, 'big')
    crc = reduce(lambda x, y: x ^ y, data, 0).to_bytes(1, 'big')
    header = b'\x02\x02\x02\x02'
    data = header + length + data + crc

    try:
        s.sendall(data)
        header = s.recv(4)
        length = s.recv(4)
        length = int.from_bytes(length, byteorder='big')
        payload = s.recv(length)
        crc = s.recv(1)
    except socket.error:
        pass
    print("<- receiving from device:")
    print(payload)
    print()

def read():
    while True:
        print("<- receiving from device:")
        try:
            header = s.recv(4)
            length = s.recv(4)
            length = int.from_bytes(length, byteorder='big')
            payload = s.recv(length)
            crc = s.recv(1)
        except socket.error:
            print("Error Occured.")
            break
        print(payload)
        print()

def stop():
    send_and_receive(b'sEN LMDscandata \x00')

if __name__ == "__main__":
    s.connect((host, port))
    try:
        # login:
        send_and_receive(b'sMN SetAccessMode \x03\xf4\x72\x47\x44')
        # -> b'\x02\x02\x02\x02\x00\x00\x00\x13sAN SetAccessMode \x009'
        send_and_receive(b'sWN EIHstCola \x01')
        # -> b'\x02\x02\x02\x02\x00\x00\x00\x05sFA\x00\n~'
        send_and_receive(b'sRN FirmwareVersion')
        # -> b'\x02\x02\x02\x02\x00\x00\x00\x1asRA FirmwareVersion \x00\x04V5.0r'

    except KeyboardInterrupt:
        print("Done.")
        try:
            stop()
        except:
            pass
        s.close()
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
