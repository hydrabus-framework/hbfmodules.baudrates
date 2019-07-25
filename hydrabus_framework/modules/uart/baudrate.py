import serial as ser
import time
from hydrabus_framework.modules.base import BaseModule
from prompt_toolkit import prompt
from serial.tools.miniterm import Miniterm


class Baudrate(BaseModule):
    """
    Iterate baudrate to find the correct value
    TODO: Add Parity bit and Stop bit option
    """
    def __init__(self):
        super(Baudrate, self).__init__()
        self.vowels = ["a", "A", "e", "E", "i", "I", "o", "O", "u", "U"]
        self.whitespace = [" ", "\t", "\r", "\n"]
        self.punctation = [".", ",", ":", ";", "?", "!"]
        self.control = [b'\x0e', b'\x0f', b'\xe0', b'\xfe', b'\xc0']
        self.baudrates = [{"dec": 9600, "hex": b'\x64'}, {"dec": 19200, "hex": b'\x65'}, {"dec": 38400, "hex": b'\x66'},
                          {"dec": 57600, "hex": b'\x67'}, {"dec": 115200, "hex": b'\x6a'}]
        self.serial = ser.Serial()
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
            # Enter UART mode
            if byte == b'\x03':
                self.serial.write(byte)
                ret = self.serial.read(4)
                return ret
            else:
                self.serial.write(byte)
                val = self.serial.read(1)
                return val
        else:
            self.logger.print_error("incorrect commands type - Bytes needed")
            return False

    def wait_ubtn(self):
        self.logger.print_user_interaction("Please press hydrabus ubtn in order to switch baudrate speed")
        while True:
            if self.serial.read(1) == 'B'.encode('utf-8'):
                if self.serial.read(3) == 'BIO'.encode('utf-8'):
                    # needed to reset interface
                    self.serial.write(b'\x0D\x0A')
                    time.sleep(0.2)
                    self.serial.read(self.serial.in_waiting)
                    break

    def set_baudrate(self, baudrate):
        """
        This function change the baudrate speed for the target device.
        It is necessary to stop echo UART RX to read the return of the
        change baudrate function from Hydrabus.
        :param baudrate: Baudrate speed dictionary (decimal and hexadecimal value)
        :return: bool
        """
        self.reset_hb()
        self.init_hb()
        # Change baudrate speed
        if b'\x01' != self.hb_commands(baudrate["hex"]):
            self.logger.print_error("Cannot set Baudrate")
            return False
        self.logger.print_success("Switching to baudrate: {}".format(baudrate["dec"]))

        # Activate echo UART RX Mode
        self.logger.print_info("Starting BBIO_UART_BRIDGE")
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

        print("Starting baurate detection, turn on your serial device now")
        print("Press Ctrl+C to cancel")

        for baudrate in self.baudrates:
            loop = 0
            if self.set_baudrate(baudrate):
                while True:
                    tmp = self.serial.read(1)
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
                            self.wait_ubtn()
                            break
                        if count >= threshold and whitespace > 0 and punctuation >= 0 and vowels > 0:
                            self.logger.print_success_result("Valid Baudrate found: {}".format(baudrate["dec"]))
                            resp = prompt('Would you like to open a miniterm session ? N/y')
                            if resp.upper() == 'Y':
                                miniterm = Miniterm(self.serial)
                                miniterm.start()
                                try:
                                    miniterm.join(True)
                                except KeyboardInterrupt:
                                    pass
                                miniterm.join()
                                miniterm.close()
                            break
                    elif loop < 3:
                        loop += 1
                        self.trigger_device()
                        continue
                    else:
                        self.wait_ubtn()
                        break
            else:
                self.wait_ubtn()
                break

    def init_hb(self):
        """
        Init the hydrabus to switch UART mode
        """
        self.logger.print_info("Switching to BBIO mode")
        for i in range(20):
            self.serial.write(b'\x00')
        if "BBIO1".encode('utf-8') not in self.serial.read(5):
            self.logger.print_info("Could not get into bbIO mode")
            quit()

        # Switching to UART mode
        if "ART1".encode('utf-8') not in self.hb_commands(b'\x03'):
            self.logger.print_info("Cannot set UART mode")
            quit()

    def reset_hb(self):
        """
        Reset hydrabus to return in console mode
        """
        self.logger.print_info("Reset hydrabus to console mode")
        self.serial.write(b'\x00')
        self.serial.write(b'\x0F')
        time.sleep(0.2)
        # clean serial buffer
        self.serial.read(self.serial.in_waiting)

    def close_hb(self):
        self.serial.close()

    def connect(self):
        ret, device = self.get_option_value("Hydrabus")
        if ret:
            try:
                self.serial = ser.Serial(device, 115200, timeout=2)
                return True
            except ser.serialutil.SerialException as err:
                self.logger.print_error(err)
        else:
            self.logger.print_error("Hydrabus value not set")
            return False

    def run(self):
        if self.connect():
            self.baudrate_detect()
            self.reset_hb()
            self.close_hb()
