import copy
import argparse
import pyrtt_viewer as rtt_viewer
import sys

DISABLE_LIMIT = 8
BLE_DATA_CHA_NUM = 37
CHN_RSSI_THRESHOLD = -90

chn_map = [1] * BLE_DATA_CHA_NUM        # initializes the chn_map list with 1, all channels are initially available.
disable_count = [0] * BLE_DATA_CHA_NUM   
processing_chn_map = False

def chn_map_update(chn_rssi_buf):
    global processing_chn_map,chn_map,disable_count
    #print(chn_rssi_buf)
    if not processing_chn_map:
        processing_chn_map = True
        for idx, rssi in enumerate(chn_rssi_buf[:BLE_DATA_CHA_NUM]):
            if rssi > CHN_RSSI_THRESHOLD:
                chn_map[idx] = 0
                disable_count[idx] = DISABLE_LIMIT           
            else:
                if disable_count[idx] == 0:
                    chn_map[idx] = 1
                else:
                    disable_count[idx] = disable_count[idx] - 1
        processing_chn_map = False
        #print(chn_map)
        #print(disable_count)

def get_current_chn_map():
    return copy.deepcopy(chn_map)

#broad 98(central),33(slave) use as QOS service module
def open_qos_device():
    parser = argparse.ArgumentParser("pyrtt-viewer")
    parser.add_argument("-s", "--segger-id", help="SEGGER ID of the nRF device", type=int)
    parser.add_argument("-c", "--channel", help="RTT channel", type=int, default=0)
    args = parser.parse_args()
    segger_id = None
    nrf = rtt_viewer.connect(segger_id)
    if not nrf:
        exit(1)
    rtt = rtt_viewer.RTT(nrf, args)
    try:
        rtt.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    rtt.run()

