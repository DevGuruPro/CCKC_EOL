import sys
import threading
import time

from PySide6 import QtCore
from PySide6.QtCore import Signal
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QApplication, QMainWindow
import keyboard

from settings import DESCRIPTION
from ui.ui_eol import Ui_EOL
from utils.can_util import CANHandler
from utils.common import convert_code_to_data, convert_time_to_data
from utils.logger import logger


class CCKCEOLApp(QMainWindow):

    sig_msg = Signal(str)

    def __init__(self):
        super().__init__()
        self.ui = Ui_EOL()
        self.ui.setupUi(self)
        self.ui.closeAppBtn.released.connect(self.close)

        screen_size = QApplication.primaryScreen().availableGeometry()
        center_x = (screen_size.width() - self.geometry().width()) // 2
        center_y = (screen_size.height() - self.geometry().height()) // 2
        self.move(center_x, center_y - 50)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)  # Qt.WindowType.Popup
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.can = CANHandler()

        self._b_stop = threading.Event()
        self._b_stop.clear()
        self._state = 'init'
        self._fsm_thread = threading.Thread(target=self._fsm)
        self._fsm_thread.start()
        self.scanned_code = ""
        self.sig_msg.connect(self._on_msg_received)

        keyboard.on_press(self.on_press)
        keyboard.on_release(self.on_release)

    def _fsm(self):
        while not self._b_stop.is_set():
            time.sleep(.001)
            if self._state == 'init':
                self.sig_msg.emit(DESCRIPTION[0])
                self._state = 'wait_can_connected'
            elif self._state == 'wait_can_connected':
                if self.can.connect():
                    self.scanned_code = ""
                    self.sig_msg.emit(DESCRIPTION[1])
                    self._state = 'scan_adb_serial'
                else:
                    time.sleep(3)
            elif self._state == 'scan_adb_serial':
                pass
            elif self._state == 'process_scanned_code':
                data = convert_code_to_data(self.scanned_code)
                if data is None:
                    self.sig_msg.emit(DESCRIPTION[2])
                    time.sleep(3)
                    self._state = 'scan_adb_serial'
                    continue
                result = self.can.handshake_data(data, compare_len=6)
                if result is None:
                    self.sig_msg.emit(DESCRIPTION[4])
                    time.sleep(3)
                    self._state = 'init'
                    continue
                elif result is False:
                    self.sig_msg.emit(DESCRIPTION[5])
                    time.sleep(3)
                    self._state = 'scan_adb_serial'
                    continue
                result = self.can.handshake_data(convert_time_to_data(), compare_len=7)
                if result is None:
                    self.sig_msg.emit(DESCRIPTION[4])
                    self._state = 'init'
                    time.sleep(3)
                    continue
                elif result is False:
                    self.sig_msg.emit(DESCRIPTION[6])
                    time.sleep(3)
                    self._state = 'scan_adb_serial'
                    continue
                self.sig_msg.emit(DESCRIPTION[7])
                self.can.disconnect()
                self._state = 'init'

    def on_press(self, event):
        self.scanned_code = self.scanned_code + event.name
        logger.debug(f"key released, scanned key: {event.name}")

    def on_release(self, event):
        if self._state == 'scan_adb_serial' and event.name == 'enter':
            logger.debug(f"ENTER released, scanned Code: {self.scanned_code}")
            self.sig_msg.emit(DESCRIPTION[2])
            self._state = 'process_scanned_code'

    def _on_msg_received(self, msg):
        self.ui.txtLabel.setText(msg)

    def closeEvent(self, event):
        self._b_stop.set()
        self._fsm_thread.join(.1)
        return super().closeEvent(event)


if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = CCKCEOLApp()
    window.show()
    sys.exit(app.exec())
