import sys
import threading
import time

from PySide6 import QtCore
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QApplication, QMainWindow
from pynput.keyboard import Listener, Key

from settings import DESCRIPTION
from ui.ui_eol import Ui_EOL
from utils.can_util import setup_can_interface, check_can_device, write_to_can, recv_from_can, wait_until_disconnected
from utils.common import convert_code_to_data, validate_writing, convert_time_to_data
from utils.logger import logger


class CCKCEOLApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_EOL()
        self.ui.setupUi(self)
        self.ui.closeAppBtn.released.connect(QApplication.instance().quit)

        screen_size = QApplication.primaryScreen().availableGeometry()
        center_x = (screen_size.width() - self.geometry().width()) // 2
        center_y = (screen_size.height() - self.geometry().height()) // 2
        self.move(center_x, center_y-50)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)  # Qt.WindowType.Popup
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
        listener_thread = threading.Thread(
            target=lambda: Listener(on_press=self.on_press, on_release=self.on_release).start())
        listener_thread.start()

    def on_press(self, key):
        try:
            if hasattr(key, 'char') and key.char:
                self.scanned_code = self.scanned_code + key.char
        except AttributeError:
            pass

    def on_release(self, key):
        if key == Key.enter:
            logger.debug(f"Scanned Code: {self.scanned_code}")
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


if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = CCKCEOLApp()
    window.show()
    sys.exit(app.exec())
