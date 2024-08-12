import can
import os
import time

from settings import ARBITRATION_ID
from utils.logger import logger


class CANHandler:

    def __init__(self, interface='can0', bitrate=500000):
        self.itf = interface
        self.bitrate = bitrate
        self.bus = None
        self.setup_interface()

    def setup_interface(self):
        os.system(f'sudo ip link set {self.itf} down')
        os.system(f'sudo ip link set {self.itf} up type can bitrate {self.bitrate}')
        logger.debug(f'{self.itf} interface set up with bitrate {self.bitrate}.')

    def connect(self):
        try:
            self.bus = can.interface.Bus(channel=self.itf, bustype='socketcan')
            msg = can.Message(arbitration_id=ARBITRATION_ID, is_remote_frame=True, is_extended_id=False)
            self.bus.send(msg, timeout=1)
            logger.info(f'Successfully sent a message on {self.itf}. The device is connected.')
            return True
        except Exception as e:
            logger.error(f'Failed to check CAN device - {e}')
            self.bus = None

    def receive(self):
        if self.bus is not None or self.connect():
            try:
                msg = self.bus.recv()
                if msg.arbitration_id == ARBITRATION_ID:
                    serial_number = msg.data
                    logger.debug(f"Received serial number {serial_number}")
                    return serial_number
            except Exception as e:
                logger.error(f"Failed to receive CAN data - {e}")
                self.bus = None

    def write(self, data):
        if self.bus is not None or self.connect():
            try:
                msg = can.Message(arbitration_id=ARBITRATION_ID, data=data, is_extended_id=False)
                self.bus.send(msg, timeout=1)
                return True
            except Exception as e:
                logger.error(f"Failed to send CAN data - {e}")
                self.bus = None

    def handshake_data(self, data, compare_len=6):
        if not self.write(data):
            return
        recv = self.receive()
        if not recv:
            return
        if data[1:compare_len] != recv[1:compare_len]:
            return False
        return True

    def disconnect(self):
        start_time = time.time()
        while True:
            try:
                msg = self.bus.recv(timeout=0.1)  # Non-blocking, wait a bit for a message
            except Exception as e:
                logger.error(f"Failed to receive CAN data to disconnect - {e}")
                self.bus = None
                return
            if msg:
                logger.debug(f"Received message: {msg}. Still connected.")
            if time.time() - start_time > 5:
                logger.debug("No message received, assuming disconnection or silence on the CAN bus.")
                return
