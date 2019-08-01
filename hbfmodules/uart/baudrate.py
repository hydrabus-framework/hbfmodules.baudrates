import serial
import time

from hydrabus_framework.modules.AModule import AModule
from hydrabus_framework.utils.logger import Logger
from hydrabus_framework.utils.hb_generic_cmd import hb_wait_ubtn, hb_reset, hb_close
from hydrabus_framework.utils.protocols.uart import hb_set_baudrate, hb_connect
from hydrabus_framework.utils.miniterm import main
from prompt_toolkit import prompt


class Baudrate(AModule):
    """
    Iterate baudrate to find the correct value
    TODO: Add Parity bit and Stop bit option
    TODO: Add all hydrabus command BBIO mode to utils directory in core framework
    """
    def __init__(self):
        super(Baudrate, self).__init__()
        self.logger = Logger()
        self.vowels = ["a", "A", "e", "E", "i", "I", "o", "O", "u", "U"]
        self.whitespace = [" ", "\t", "\r", "\n"]
        self.punctation = [".", ",", ":", ";", "?", "!"]
        self.control = [b'\x0e', b'\x0f', b'\xe0', b'\xfe', b'\xc0']
        self.baudrates = [{"dec": 9600, "hex": b'\x64'}, {"dec": 19200, "hex": b'\x65'}, {"dec": 38400, "hex": b'\x66'},
                          {"dec": 57600, "hex": b'\x67'}, {"dec": 115200, "hex": b'\x6a'}]
        self.serial = serial.Serial()
        self.description = "Automatically detect baudrate of a target device"
        self.options = [
            {"Name": "Hydrabus", "Value": "", "Required": True, "Type": "string",
             "Description": "Hydrabus device", "Default": "/dev/ttyACM0"},
            {"Name": "timeout", "Value": "", "Required": True, "Type": "int",
             "Description": "Hydrabus read timeout", "Default": 2},
        ]

    def gen_char_list(self):
        """
        Generate human readable characters list.
        :return: character's list
        """
        c = ' '
        valid_characters = []
        while c <= '~':
            valid_characters.append(c)
            c = chr(ord(c) + 1)

        for c in self.whitespace:
            if c not in valid_characters:
                valid_characters.append(c)

        for c in self.control:
            if c not in valid_characters:
                valid_characters.append(c)
        return valid_characters

    def hb_commands(self, byte):
        """
        This function write one byte then read the returned value
        :param byte: The function in byte format sent to hydrabus
        :return: the last byte received
        """
        if isinstance(byte, bytes):
            self.serial.write(byte)
            val = self.serial.read(1)
            return val
        else:
            self.logger.handle("incorrect commands type - Bytes needed", Logger.ERROR)
            return False

    def change_baudrate(self, baudrate):
        """
        This function change the baudrate speed for the target device.
        It is necessary to stop echo UART RX to read the return of the
        change baudrate function from Hydrabus.
        :param baudrate: Baudrate speed dictionary (decimal and hexadecimal value)
        :return: bool
        """
        if not hb_set_baudrate(self.serial, baudrate):
            return False
        else:
            # Activate echo UART RX Mode
            self.logger.handle("Starting BBIO_UART_BRIDGE", Logger.INFO)

            self.hb_commands(b'\x0F')
            return True

    def trigger_device(self):
        """
        Send a carriage return to trigger the target device
        in case no byte(s) is received
        """
        self.serial.write(b'\x0D\x0A')
        time.sleep(0.2)

    def baudrate_detect(self):
        """
        The main function. Change the baudrate speed
        and check if the received byte(s) from RX pin are valid characters.
        25 valid characters are required to identify the correct baudrate value.
        """
        count = 0
        whitespace = 0
        punctuation = 0
        vowels = 0
        threshold = 25
        valid_characters = self.gen_char_list()

        self.logger.handle("Starting baurate detection, turn on your serial device now", Logger.HEADER)
        self.logger.handle("Press Ctrl+C to cancel", Logger.HEADER)

        for baudrate in self.baudrates:
            loop = 0
            if self.change_baudrate(baudrate):
                while True:
                    tmp = self.serial.read(1)
                    print(tmp)
                    # TODO: Print readed bytes in dynamic manner
                    if len(tmp) > 0:
                        try:
                            byte = tmp.decode('utf-8')
                        except UnicodeDecodeError:
                            byte = tmp
                        if byte in valid_characters:
                            if byte in self.whitespace:
                                whitespace += 1
                            elif byte in self.punctation:
                                punctuation += 1
                            elif byte in self.vowels:
                                vowels += 1
                            count += 1
                        else:
                            whitespace = 0
                            punctuation = 0
                            vowels = 0
                            count = 0
                            self.logger.handle("Please press hydrabus ubtn in order to switch baudrate speed",
                                              Logger.USER_INTERACT)
                            hb_wait_ubtn(self.serial)
                            break
                        if count >= threshold and whitespace > 0 and punctuation >= 0 and vowels > 0:
                            self.logger.handle("Valid Baudrate found: {}".format(baudrate["dec"]), Logger.RESULT)
                            resp = prompt('Would you like to open a miniterm session ? N/y: ')
                            if resp.upper() == 'Y':
                                hb_close(self.serial)
                                main('/dev/ttyACM0', 115200)
                            break
                    elif loop < 3:
                        loop += 1
                        self.trigger_device()
                        continue
                    else:
                        self.logger.handle("Please press hydrabus ubtn in order to switch baudrate speed",
                                           Logger.USER_INTERACT)
                        hb_wait_ubtn(self.serial)
                        break
            else:
                self.logger.handle("Please press hydrabus ubtn in order to switch baudrate speed", Logger.USER_INTERACT)
                hb_wait_ubtn(self.serial)
                break

    def connect(self):
        ret, device = self.get_option_value("Hydrabus")
        if ret:
            self.serial = hb_connect(device=device, baudrate=115200, timeout=1)
            if not self.serial:
                return False
            return True
        else:
            self.logger.handle("Hydrabus value not set", Logger.ERROR)
            return False

    def run(self):
        if self.connect():
            self.baudrate_detect()
            self.logger.handle("Reset hydrabus to console mode", Logger.INFO)
            hb_reset(self.serial)
            hb_close(self.serial)
