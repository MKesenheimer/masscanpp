#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import masscan
import random
import time
import json

port=80

if __name__ == "__main__":
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
            print(ip_range)
            try:
                mas = masscan.PortScanner()
                mas.scan(ip_range, ports=str(port), arguments='--max-rate 262144')
                delay = 5000
                scan_result = json.loads(mas.scan_result)
                #print(scan_result['scan'])
                for ip in scan_result['scan']:
                    status = scan_result['scan'][ip][0]
                    print(f"{ip} {status}")
                    if 'tcp' in status['proto'] and port == status['port'] and 'open' in status['status']:
                        print(f"checking status of {ip}:{port}")
                        #status.send_with_options(args=(ip, ), delay=delay)
                        delay += 5000
            except masscan.NetworkConnectionError:
                print(f"{ip_range} masscan masscan.NetworkConnectionError")
                time.sleep(30)
        print('done scanning')
