#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2018 Thomas Stenersen
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS  "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WAPROVIDEDRRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import time
import threading
import logging
import argparse
import copy
import chn_map_process as cmp
try:
    from pynrfjprog.API import API
    from pynrfjprog.API import DeviceFamily as NrfDeviceFamily
except ImportError:
    print("Error: Could not find pynrfjprog.")
    print("Did you run `pip install pynrfjprog`?")
    sys.exit(1)

chn_rssi_buffer = [] #buffer used to store channel rssi map

def get_snr(nrf):
    devices = nrf.enum_emu_snr()
    if devices and len(devices) > 0:
        device_range = list(range(len(devices)))
        print("Connected devices:")
        print("".join(["%d: %d\n" % (i, devices[i]) for i in device_range]))

        number = None
        while number is None:
            try:
                number = input("Select a device number or quit (q): ")
                if number == "q":
                    return None
                elif int(number) in device_range:
                    return devices[int(number)]
            except ValueError:
                pass

            print("Invalid input \"%s\"" % (number))
            number = None
    else:
        print("No devices connected.")

def connect(snr=None, jlink_khz=50000):
    nrf = API(NrfDeviceFamily.NRF52)
    nrf.open()
    if not snr:
        snr = get_snr(nrf)

    if not snr:
        nrf.close()
        return None

    nrf.connect_to_emu_with_snr(snr, jlink_khz)
    try:
        _version = nrf.read_device_version()  # noqa F81: unused variable
    except API.APIError as e:
        if e.err_code == API.NrfjprogdllErr.WRONG_FAMILY_FOR_DEVICE:
            nrf.close()
            nrf = API(NrfDeviceFamily.NRF52)
            nrf.open()
            if snr:
                nrf.connect_to_emu_with_snr(snr, jlink_khz)
            else:
                nrf.connect_to_emu_without_snr(jlink_khz)
        else:
            raise e
    return nrf

def list_devices():
    nrf = API(NrfDeviceFamily.NRF52)
    nrf.open()
    devices = nrf.enum_emu_snr()
    if devices:
        print("\n".join(list(map(str, devices))))
        nrf.close()
        
class RTT:
    """RTT commication class"""
    def __init__(self, nrf, args):
        self._args = args
        self._nrf = nrf
        self._close_event = None
        self._writer_thread = None
        self._reader_thread = None

    def _writer(self):
        while not self._close_event.is_set():
            data = sys.stdin.readline().strip("\n")
            if len(data) > 0:
                self._nrf.rtt_write(self._args.channel, data)
            time.sleep(0.1)

    def _reader(self):
        BLOCK_SIZE = 512
        rtt_data = ""
        global chn_map
        while not self._close_event.is_set():
            rtt_data = self._nrf.rtt_read(self._args.channel, BLOCK_SIZE)

            if rtt_data == "" or type(rtt_data) == int:
                time.sleep(0.1)
                continue
            rtt_data = rtt_data.rstrip("\r\n")
            for s in rtt_data.splitlines():
                if s.strip() == "":
                    continue
                
                if not s.strip().startswith("<debug> app:"):
                    continue
                chn_rssi = s.strip().split(",")[1]
                
                for chn_idx in chn_rssi.split():
                     if(len(chn_rssi_buffer)>=40):
                         chn_rssi_buffer.clear()
                     chn_rssi_buffer.append(int(chn_idx))
                
                '''
                try:
                    sys.stdout.buffer.write(bytes(s, "ascii"))
                except TypeError:
                    continue
                '''
                
                if(len(chn_rssi_buffer)>=40):
                    cmp.chn_map_update(chn_rssi_buffer)
                    
                

                #sys.stdout.buffer.write(b'\n')
                #sys.stdout.buffer.flush()

    def run(self):
        self._nrf.rtt_start()

        # Wait for RTT to find control block etc.
        time.sleep(0.5)
        while not self._nrf.rtt_is_control_block_found():
            logging.info("Looking for RTT control block...")
            self._nrf.rtt_stop()
            time.sleep(0.5)
            self._nrf.rtt_start()
            time.sleep(0.5)

        self._close_event = threading.Event()
        self._close_event.clear()
        self._reader_thread = threading.Thread(target=self._reader)
        self._reader_thread.start()
        self._writer_thread = threading.Thread(target=self._writer)
        self._writer_thread.start()
        try:
            while self._reader_thread.is_alive() or \
                  self._writer_thread.is_alive():
                time.sleep(0.1)
        except KeyboardInterrupt:
            self._close_event.set()
            self._reader_thread.join()
            self._writer_thread.join()


def main():
    parser = argparse.ArgumentParser("pyrtt-viewer")
    parser.add_argument("-s", "--segger-id", help="SEGGER ID of the nRF device", type=int)
    parser.add_argument("-c", "--channel", help="RTT channel", type=int, default=0)
    args = parser.parse_args()
    nrf = connect(args.segger_id)
    if not nrf:
        exit(1)

    rtt = RTT(nrf, args)
    try:
        rtt.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    rtt.run()


if __name__ == "__main__":
    main()
