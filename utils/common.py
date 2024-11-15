from datetime import datetime

from utils.logger import logger


def convert_code_to_data(scan_code=""):
    scan_code = scan_code.replace('\u2212', '-')
    part_code = scan_code.split('-')
    adb_version = int(part_code[0][3:])
    version_data = adb_version.to_bytes(1, 'big')
    if len(part_code[1]) > 9:
        return
    num = int(part_code[1])
    serial_data = num.to_bytes(4, 'big')
    data = bytearray([0x01]) + serial_data + version_data + bytearray([0x2A, 0xFF])
    logger.debug(f'Scanned Code -> byte data : {data}')
    return data


def convert_time_to_data():
    date_num = [datetime.now().year - 2000, datetime.now().month, datetime.now().day,
                datetime.now().hour, datetime.now().minute]
    serial_data = bytearray()
    for num in date_num:
        serial_data.append(num.to_bytes(1, 'big')[0])
    data = bytearray([0x04]) + serial_data + bytearray([0x43, 0x4E])
    logger.debug(f"Date,Time,Location - > byte data: {data}")
    return data
