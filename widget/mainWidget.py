import os
import time
import can
import threading
from datetime import datetime

from utils.logger import logger
from PySide6 import QtCore
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QMainWindow

from pynput.keyboard import Key, Listener

from ui.ui_eol import Ui_EOL

ARBITRATION_ID = 0x7F
DESCRIPTION = ["Please connect a CAN bus.\n请连接CAN总线.",
               "Please scan a QR code.\n请扫描二维码.",
               "Serial number is not valid.\nPlease scan again.\n序列号无效.请重新扫描.",
               "Date,Time,Manufacturing code are not valid.\nPlease scan again.\n日期,时间,制造代码无效.请重新扫描.",
               "Operation completed successfully.\nPlease connect a new device.\n操作已成功完成.请连接新设备."]


def setup_can_interface(interface='can0', bitrate=500000):
    os.system(f'sudo ip link set {interface} down')
    os.system(f'sudo ip link set {interface} up type can bitrate {bitrate}')
    logger.debug(f'{interface} interface set up with bitrate {bitrate}.')


def wait_until_disconnected(interface='can0',timeout=1):
    try:
        bus = can.interface.Bus(channel=interface, bustype='socketcan')
    except Exception as e:
        logger.debug(f"Error creating bus {interface}: {str(e)}")
        return

    start_time = time.time()
    while True:
        msg = bus.recv(timeout=0.1)  # Non-blocking, wait a bit for a message
        if msg:
            logger.debug(f"Received message: {msg}. Still connected.")
        if time.time() - start_time > timeout:
            logger.debug("No message received, assuming disconnection or silence on the CAN bus.")
            return


def check_can_device(interface='can1'):
    try:
        bus = can.interface.Bus(channel=interface, bustype='socketcan')
        msg = can.Message(arbitration_id=ARBITRATION_ID, is_remote_frame=True, is_extended_id=False)
        bus.send(msg, timeout=1)
        logger.info(f'Successfully sent a message on {interface}. The device is connected.')
    except OSError:
        logger.error(f'Error: Could not send a message on {interface}. Will retry...')
        return False
    except can.CanError as e:
        logger.error(f'CAN Error: {str(e)}')
        return False


def recv_from_can(interface='can0'):
    try:
        bus = can.interface.Bus(channel=interface, bustype='socketcan')
        while True:
            msg = bus.recv()
            if msg.arbitration_id == ARBITRATION_ID:
                serial_number = msg.data
                logger.debug(f"Received serial number {serial_number}")
                return serial_number
    except OSError:
        logger.error(f'Error: Could not receive a message on {interface}.')
        return False
    except can.CanError as e:
        logger.error(f'CAN Error: {str(e)}')
        return False


def convert_code_to_data(scan_code=""):
    part_code = scan_code.split('-')
    adb_version = int(part_code[0][3:])
    version_data = adb_version.to_bytes(1, 'big')
    num = int(part_code[1])
    serial_data = num.to_bytes(4, 'big')
    data = bytearray(0x01) + serial_data + version_data + bytearray([0x2A, 0xFF])
    logger.debug(f'Scanned Code -> byte data : {data}')
    return data


def validate_writing(send_data, recv_data):
    for i in range(len(send_data)):
        if send_data[i] != recv_data[i]:
            return False
    return True


def convert_time_to_data():
    date_num = [datetime.now().year, datetime.now().month, datetime.now().day,
                datetime.now().hour, datetime.now().minute]
    serial_data = bytearray()
    for num in date_num:
        serial_data.append(num.to_bytes(1, 'big')[0])
    data = bytearray(0x04) + serial_data + serial_data + bytearray([0x43,0x4E])
    logger.debug(f"Date,Time,Location - > byte data: {data}")
    return data

def write_to_can(interface='can1', serial_data=bytearray()):
    try:
        bus = can.interface.Bus(channel=interface, bustype='socketcan')
        msg = can.Message(arbitration_id=ARBITRATION_ID, data=serial_data, is_extended_id=False)
        bus.send(msg, timeout=1)
        logger.debug(f"Write serial number {serial_data}")
        return
    except OSError:
        logger.error(f'Error: Could not receive a message on {interface}.')
        return False
    except can.CanError as e:
        logger.error(f'CAN Error: {str(e)}')
        return False


class MainWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_EOL()
        self.ui.setupUi(self)
        self.ui.closeAppBtn.released.connect(QApplication.instance().quit)

        screen_size = QApplication.primaryScreen().availableGeometry()
        center_x = (screen_size.width() - self.geometry().width()) // 2
        center_y = (screen_size.height() - self.geometry().height()) // 2
        self.move(center_x, center_y-50)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint ) #| Qt.WindowType.Popup
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.scanned_code = ""
        self.start_process()

    def start_process(self):
        self.start_can_watch_thread()
        self.scanned_code = ""
        self.ui.txtLabel.setText(DESCRIPTION[0])

    def start_can_watch_thread(self, interface='can0', retry_interval=5):
        thread = threading.Thread(target=self.wait_for_can_connection, args=(interface, retry_interval), daemon=True)
        thread.start()

    def wait_for_can_connection(self, interface, retry_interval):
        setup_can_interface(interface)
        while True:
            if check_can_device(interface):
                logger.debug(f"{interface} is operational. Exiting thread.")
                # if check_valid_serial():
                #     self.ui.txtLabel.setText(f"Serial number detected. Please connect new device.")
                #     self.start_can_watch_thread()
                # else:
                self.ui.txtLabel.setText(f"Please scan ADB serial number.")
                self.scan_adb_serial()
                break
            else:
                logger.debug(f"Waiting for {interface} to become operational...")
                time.sleep(retry_interval)

    def scan_adb_serial(self):
        self.scanned_code = ""
        listener_thread = threading.Thread(target=lambda: Listener(on_press=self.on_press, on_release=self.on_release).start())
        listener_thread.start()

    def on_press(self, key):
        try:
            if hasattr(key, 'char') and key.char:
                self.scanned_code = self.scanned_code + key.char
        except AttributeError:
            pass

    def on_release(self, key):
        if key == Key.enter:
            print(f"Scanned Code: {self.scanned_code}")
            send_data = convert_code_to_data(self.scanned_code)
            self.scanned_code = ""
            write_to_can(serial_data=send_data)
            recv_data = recv_from_can()
            if validate_writing(send_data[1:6], recv_data[1:6]) is False:
                self.ui.txtLabel.setText(DESCRIPTION[2])
                self.scan_adb_serial()
                return
            send_data = convert_time_to_data()
            write_to_can(serial_data=send_data)
            recv_data = recv_from_can()
            if validate_writing(send_data[1:7], recv_data[1:7]) is False:
                self.ui.txtLabel.setText(DESCRIPTION[3])
                self.scan_adb_serial()
                return
            self.ui.txtLabel.setText(DESCRIPTION[4])
            wait_until_disconnected()
            self.start_process()

