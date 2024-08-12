import json
import os

_cur_dir = os.path.dirname(os.path.realpath(__file__))

ROOT_DIR = os.path.expanduser('~/.eol')
os.makedirs(ROOT_DIR, exist_ok=True)

DEFAULT_CONFIG = {

}

CONFIG_FILE = os.path.join(ROOT_DIR, 'config.json')
if not os.path.exists(CONFIG_FILE):
    print("No config found! Creating the default one...")
    with open(CONFIG_FILE, 'w') as jp:
        json.dump(DEFAULT_CONFIG, jp, indent=2)


ADDRESS_HW = 0xCF
ADDRESS_RPI = 0x7F

DESCRIPTION = ["Please connect a CAN bus.\n请连接CAN总线.",
               "Please scan a QR code.\n请扫描二维码.",
               "Writing...\n现在正在写..."
               "Failed to connect to a CAN.\n无法连接到 CAN."
               "Serial number is not valid.\nPlease scan again.\n序列号无效.请重新扫描.",
               "Date,Time,Manufacturing code are not valid.\nPlease scan again.\n日期,时间,制造代码无效.请重新扫描.",
               "Operation completed successfully.\nPlease connect a new device.\n操作已成功完成.请连接新设备."]

CAN_RECV_ITF = 'can0'
CAN_SEND_ITF = 'can1'

try:
    from local_settings import *
except ImportError:
    pass
