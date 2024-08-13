import can
import os

from settings import CAN_RECV_ITF, CAN_SEND_ITF, RECV_ARBITRATION_ID, SEND_ARBITRATION_ID
from utils.logger import logger


class CANHandler:

    def __init__(self, bitrate=250000):
        self.bitrate = bitrate
        self.send_bus = None
        self.recv_bus = None
        self.setup_interface(CAN_RECV_ITF)
        self.setup_interface(CAN_SEND_ITF)

    def setup_interface(self, interface):
        os.system(f'sudo ip link set {interface} down')
        os.system(f'sudo ip link set {interface} up type can bitrate {self.bitrate}')
        logger.debug(f'{interface} interface set up with bitrate {self.bitrate}.')

    def connect(self):
        try:
            self.recv_bus = can.interface.Bus(channel=CAN_RECV_ITF, bustype='socketcan')
            self.send_bus = can.interface.Bus(channel=CAN_SEND_ITF, bustype='socketcan')
            msg = can.Message(arbitration_id=SEND_ARBITRATION_ID, is_remote_frame=True, is_extended_id=False)
            self.send_bus.send(msg, timeout=1)
            logger.info(f'Successfully sent a message on {CAN_SEND_ITF}. The device is connected.')
            return True
        except Exception as e:
            logger.error(f'Failed to check CAN device - {e}')
            self.recv_bus = None
            self.send_bus = None

    def receive(self):
        if self.recv_bus is not None or self.connect():
            try:
                msg = self.recv_bus.recv()
                if msg.arbitration_id == RECV_ARBITRATION_ID:
                    serial_number = msg.data
                    logger.debug(f"Received serial number {serial_number}")
                    return serial_number
            except Exception as e:
                logger.error(f"Failed to receive CAN data - {e}")
                self.recv_bus = None

    def write(self, data):
        if self.send_bus is not None or self.connect():
            try:
                msg = can.Message(arbitration_id=SEND_ARBITRATION_ID, data=data, is_extended_id=False)
                self.send_bus.send(msg, timeout=1)
                return True
            except Exception as e:
                logger.error(f"Failed to send CAN data - {e}")
                self.send_bus = None

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
        while True:
            try:
                msg = self.recv_bus.recv(timeout=0.1)  # Non-blocking, wait a bit for a message
                logger.debug(f"Received message: {msg}. Still connected.")
            except (can.CanError, OSError):
                logger.debug("No message received, assuming disconnection or silence on the CAN bus.")
                self.recv_bus = None
                return
