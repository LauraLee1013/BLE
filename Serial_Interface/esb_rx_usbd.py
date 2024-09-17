import threading
import time
from datetime import datetime

from time import sleep
import serial
import sys
import queue
import pandas as pd
import csv
import sys
import struct
import chn_map_process as cmp
import hashlib

CDC_ACM_DATA = 0
CDC_ACM_CHN_UPDATE = 1
URLLC_DATA_INTERVAL = 0.1  # sleep URLLC_DATA_INTERVAL(seconds) between sending data(sync or urllc) to comport
CHA_MAP_UPDATE_INTERVAL = 2
CHN_MAP_UPDATE_OFFSET = 0.2
CDC_ACM_DATA_MAX_SIZE = 256  # maximum data bytes that can tranfer each time

com_list = ['com3','com13','com17','com20','com23']

# com_list = ['com17', 'com18']
#com_list = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyACM2', '/dev/ttyACM3', '/dev/ttyACM4']
#com_list = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyACM2']
com_threads = {}
com_lock = threading.Lock()  # Lock for synchronizing access to com_queue


def read_data(ser, q):
    while (True):
        queue = ser.inWaiting()
        if queue > 0:
            data = ser.read_all().decode('utf-8').split(',')
            data.append(ser.port)
            q.put(data)
            # print(data)


def com_port_init(data_queue):
    for com_name in com_list:
        try:
            opened_com = serial.Serial(com_name, 115200, timeout=0.5)
            # assigned read_data task to thread for relative comport and start it immediately
            read_thread = threading.Thread(target=read_data, args=(opened_com, data_queue))
            read_thread.start()
        except serial.SerialException as e:
            print(f"Failed to open COM port {com_name}. Error: {str(e)}")



def check_data(queue, max_count):
    num = 0
    count = 0
    err = 0
    start_time = time.time()

    with open('log_test_v1.txt', 'w') as log_file:
        # while True:
        while count < max_count:
            data = queue.get() 
            current_time = time.time()
            # log_file.write(f"{datetime.now()}\n")
         
            if data[0].isdigit() and int(data[0]) > num:
                if int(data[0]) != num + 1:
                    err_msg = f"Lost packet at expected sequence {num + 1}. Actual sequence {data[0]}"
                    print(err_msg)
                    err += 1
                
                    log_file.write(f"{datetime.now()}: {err_msg}\n")
                num = int(data[0])
                
                if hashlib.md5(str(data[0]).encode()).hexdigest() != data[2]:
                    err_msg = f"Hash mismatch on sequence {data[0]}"
                    print(err_msg)
                    err += 1
                    log_file.write(f"{datetime.now()}: {err_msg}\n")
                    log_file.flush()         
                                        
                # log_file.write(f"{datetime.now()}: {err_msg}\n")
                count += 1
                print(f"S: {data[0]}, D: {data[2]}, C: {count}, L: {data[1]}, E: {err}, P: {data[4]}, T: {round((current_time-start_time)*1000)}, RSSI: -{data[3]}dbm")


def main():
    data_queue = queue.Queue(1000)
    com_port_init(data_queue)
    # check_data(data_queue)
    check_data(data_queue, 100000)

if __name__ == '__main__':
    main()