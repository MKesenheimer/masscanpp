#!/usr/bin/env python3
# -*- conding: utf-8 -*-

import socket
import sys
import os
from binascii import hexlify, unhexlify

host = '192.168.11.150'
#host = socket.gethostname()
port = 2111
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def send_and_receive(data: bytes):
    print("-> sending to device:")
    print(data)
    print()
    try:
        s.sendall(data)
        data = s.recv(1024)
    except socket.error:
        pass
    print("<- receiving from device:")
    print(data)
    print()

def init():
    send_and_receive(b'\x02sRI 0\x03')
    send_and_receive(b'\x02sMI 5 3 F4724744\x03')
    #send_and_receive(b'\x02sEI 5A 1\x03')

def read():
    # read continuously
    try:
        s.sendall(b'\x02sEI 5A 1\x03')
    except socket.error:
        print("Error Occured.")
    while True:
        print("<- receiving from device:")
        try:
            data = s.recv(1024)
        except socket.error:
            print("Error Occured.")
            break
        print(data)
        print()

def stop():
    send_and_receive(b'\x02sEI 5A 0\x03')
    send_and_receive(b'\x02sEI 88 0\x03')

if __name__ == "__main__":
    s.connect((host, port))
    try:
        init()

        # developer login
        send_and_receive(b'\x02sMN CheckPassword 07 ...\x03')
        
        #read()
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
