import can
import os
import time

from settings import ARBITRATION_ID
from utils.logger import logger


def setup_can_interface(interface='can0', bitrate=500000):
    os.system(f'sudo ip link set {interface} down')
    os.system(f'sudo ip link set {interface} up type can bitrate {bitrate}')
    logger.debug(f'{interface} interface set up with bitrate {bitrate}.')


def wait_until_disconnected(interface='can0', timeout=1):
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
