#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import serial
import os
import time
import tempfile
from .filelock import FileLock


actual_codes = {}
common_codes = {
    'aspect43'      : b"kc 00 01",
    'aspect169'     : b"kc 00 02",
    'aspectstatus'  : b"kc 00 ff",
    'poweroff'      : b"ka 00 00",
    'poweron'       : b"ka 00 01",
    'powerstatus'   : b"ka 00 ff",
    'volumelevel'   : b"kf 00 ff",
    'mute'          : b"ke 00 00",
    'unmute'        : b"ke 00 01",
    'mutestatus'    : b"ke 00 ff"
}
actual_codes['LK450_etc'] = {
    'inputdigitalantenna'   : b"xb 00 00",
    'inputdigitalcable'     : b"xb 00 01",
    'inputanalogantenna'    : b"xb 00 10",
    'inputanalogcable'      : b"xb 00 11",
    'inputav1'              : b"xb 00 20",
    'inputav2'              : b"xb 00 21",
    'inputcomp1'            : b"xb 00 40",
    'inputcomp2'            : b"xb 00 41",
    'inputrgbpc'            : b"xb 00 60",
    'inputhdmi1'            : b"xb 00 90",
    'inputhdmi2'            : b"xb 00 91",
    'inputhdmi3'            : b"xb 00 92",
    'inputhdmi4'            : b"xb 00 93",
    'inputstatus'           : b"xb 00 ff"
}
actual_codes['PJ250_etc'] = {
    'inputdtvantenna'       : b"xb 00 00",
    'inputdtvcable'         : b"xb 00 01",
    'inputanalogantenna'    : b"xb 00 10",
    'inputanalogcable'      : b"xb 00 11",
    'inputav1'              : b"xb 00 20",
    'inputav2'              : b"xb 00 21",
    'inputcomp1'            : b"xb 00 40",
    'inputcomp2'            : b"xb 00 41",
    'inputrgbpc'            : b"xb 00 60",
    'inputhdmi1'            : b"xb 00 90",
    'inputhdmi2'            : b"xb 00 91",
    'inputhdmi3'            : b"xb 00 92",
    'inputstatus'           : b"xb 00 ff"
}
actual_codes['LE5300_etc'] = {
    'inputdtv'              : b"xb 00 00",
    'inputanalogantenna'    : b"xb 00 10",
    'inputanalogcable'      : b"xb 00 11",
    'inputav1'              : b"xb 00 20",
    'inputav2'              : b"xb 00 21",
    'inputcomp'             : b"xb 00 40",
    'inputrgbpc'            : b"xb 00 60",
    'inputhdmi1'            : b"xb 00 90",
    'inputhdmi2'            : b"xb 00 91",
    'inputhdmi3'            : b"xb 00 92",
    'inputhdmi4'            : b"xb 00 93",
    'inputstatus'           : b"xb 00 ff"
}
actual_codes['LC7D_etc'] = {
    'inputdtvantenna'       : b"xb 00 00",
    'inputdtvcable'         : b"xb 00 01",
    'inputanalogantenna'    : b"xb 00 10",
    'inputanalogcable'      : b"xb 00 11",
    'inputav1'              : b"xb 00 20",
    'inputav2'              : b"xb 00 21",
    'inputcomp1'            : b"xb 00 40",
    'inputcomp2'            : b"xb 00 41",
    'inputrgbpc'            : b"xb 00 60",
    'inputhdmi1'            : b"xb 00 90",
    'inputhdmi2'            : b"xb 00 91",
    'inputstatus'           : b"xb 00 ff"
}
actual_codes['01C_etc'] = {
    'inputav'       : b"kb 00 02",
    'inputcomp1'    : b"kb 00 04",
    'inputcomp2'    : b"kb 00 05",
    'inputrgbdtv'   : b"kb 00 06",
    'inputrgbpc'    : b"kb 00 07",
    'inputhdmidtv'  : b"kb 00 08",
    'inputhdmipc'   : b"kb 00 09",
    'inputstatus'   : b"kb 00 ff"
}
actual_codes['02C_etc'] = {
    'inputav'       : b"kb 00 02",
    'inputcomp1'    : b"kb 00 04",
    'inputcomp2'    : b"kb 00 05",
    'inputrgbpc'    : b"kb 00 07",
    'inputhdmidtv'  : b"kb 00 08",
    'inputhdmipc'   : b"kb 00 09",
    'inputstatus'   : b"kb 00 ff"
}
actual_codes['LB5D_etc'] = {
    # NOTE: There is also a kb input control command, but at least on a 42LB5D
    # they don't seem able to select HDMI3. They also have a similar offset
    # issue past rgbpc as described below.
    'inputdigitalantenna': b"xb 00 00",
    'inputdigitalcable': b"xb 00 01",
    'inputanalogantenna': b"xb 00 10",
    'inputanalogcable': b"xb 00 11",
    'inputav1': b"xb 00 20",
    'inputav2': b"xb 00 21",
    'inputcomp1': b"xb 00 40",
    'inputcomp2': b"xb 00 41",
    # NOTE: The last byte for the rest of these is different than what is
    # specified in the manual.
    'inputrgbpc': b"xb 00 60",
    'inputhdmi1': b"xb 00 90",
    'inputhdmi2': b"xb 00 91",
    'inputhdmi3': b"xb 00 92",
    'inputstatus': b"xb 00 ff",
}
actual_codes['C3PUA_etc'] = {
    'inputhdmi1': b"xb 00 90",
    'inputhdmi2': b"xb 00 91",
    'inputhdmi3': b"xb 00 92",
    'inputhdmi4': b"xb 00 93",
    'inputstatus': b"xb 00 ff",
}
reverse_code_map = {
    'LK450_etc': ('LV2500', 'LV2520', 'LV3500', 'LV3520', 'LK330', 'LK430', 'LK450',
                    'LK520', 'PW340', 'PW350', 'PW350U', 'PW350R', 'LH20', 'LH200C',
                    'LH30', 'LF11', 'LF21', 'LU55', 'CL10', 'CL20', 'CL11', 'PZ200'),
    'PJ250_etc': ('PJ250', 'PK250', 'PK280', 'PK290', 'PJ340', 'PJ350', 'PK350',
                    'PKPK340', 'PK540', 'PJ550', 'PK550', 'PJ350C', 'PK550C'),
    'LC7D_etc': ('LC7D', 'LC7DC', 'PC5D', 'PC5DC'),
    'LE5300_etc': ('LE5300', 'LE5500', 'LE7300', 'LE530C', 'LD420', 'LD450', 'LD450C',
                    'LD520', 'LD520C', 'LD630', 'LW5600', 'LW5700', 'LW6500', 'LW9800',
                    'LV3700', 'LV5400', 'LV5500', 'LV9500', 'LK530', 'LK550', 'PZ750',
                    'PZ950', 'PZ950U'),
    '01C_etc': ('01C', '01C-BA'),
    '02C_etc': ('02C', '02C-BA', '02C-BH'),
    'LB5D_etc': ('LB5D', 'LB4D'),
    'C3PUA_etc': ('C3PUA',),
}
all_codes = {}
# populate model suffix lookup hash
for suffix_codes, suffixes in reverse_code_map.items():
    for suffix in suffixes:
        codes = common_codes.copy()
        codes.update(actual_codes[suffix_codes])
        all_codes[suffix] = codes


class LGTV:
    default_serial = '/dev/ttyUSB0'

    @staticmethod
    def data_to_int(data):
        return int(data.decode(), base=16)

    def __init__(self, model, port=None, verbose=False):
        self.model = model.upper()
        self.verbose = verbose

        # Ignore digits which indicate the TV's screen size
        if model.startswith('M'):
            self.codes = all_codes[self.model[3:]]  # Ignore the leading 'M' too
        else:
            self.codes = all_codes[self.model[2:]]
        self.inputs_by_data = {self.data_to_int(v[-2:]): k[5:] for k, v in self.codes.items()
            if k.startswith('input') and not k.endswith('status')}

        self.port = port if port is not None else default_serial
        self.connection = None
        self.toggles = {
            'togglepower': ('poweron', 'poweroff'),
            'togglemute': ('mute', 'unmute'),
        }
        self.debounces = {}

    #this next line sets up the serial port to allow for communication
    #and opens the serial port you may need to change
    #ttyS0 to S1, S2, ect. The rest shouldn't need to change.
    def get_port(self):
        return serial.Serial(self.port, 9600, 8, serial.PARITY_NONE,
                serial.STOPBITS_ONE, xonxoff=0, rtscts=0, timeout=1)

    def get_port_ensured(self):
        ser = None
        while ser == None:
            try:
                ser = self.get_port()
            except serial.serialutil.SerialException:
                time.sleep(0.07)
        return ser

    def status_code(self, code):
        return code[:-2] + b'ff'

    @staticmethod
    def insert_data(code, data_arg):
        if data_arg is not None:
            if not isinstance(data_arg, int):
                raise TypeError(f'data {repr()} is not an int')
            if data_arg < 0 or data_arg > 255:
                raise ValueError(f'data {repr()} is can not fit in a byte')
            code = code[:-2] + f'{data_arg:02x}'[-2:].encode()
        return code

    def lookup(self, command, data_arg):
        if command.startswith('toggle'):
            states = self.toggles.get(command)
            state_codes = (self.codes[states[0]], self.codes[states[1]])
            return self.toggle(self.status_code(state_codes[0]), state_codes)
        elif command.endswith('up'):
            key = command[:-2] + 'level'
            return self.increment(self.status_code(self.codes[key]))
        elif command.endswith('down'):
            key = command[:-4] + 'level'
            return self.decrement(self.status_code(self.codes[key]))
        else:
            return self.insert_data(self.codes[command], data_arg)

    # Returns None on error, full response otherwise
    def query_full(self, code):
        if self.verbose:
            print('Send:', code)
        self.connection.write(code + b'\r')
        response = self.connection.read(10)
        if self.verbose:
            print('Receive:', response)
        if self.is_success(response):
            return response

    def query_data(self, code):
        response = self.query_full(code)
        return response and response[-3:-1]

    # returns None on error, 2-char status for status commands, and True otherwise
    def query(self, command, data_arg):
        command_seq = self.lookup(command, data_arg)
        if self.is_status(command):
            return self.query_data(command_seq)
        else:
            return self.query_full(command_seq) and True

    def is_status(self, command):
        return command.endswith('status') or command.endswith('level')

    def is_success(self, response):
        return response[-5:-3] == b'OK'

    def hex_bytes_delta(self, hex_bytes, delta):
        value = int(hex_bytes, 16) + delta
        if value < 0 or value > 255:
            raise ValueError(f'{value:02x} is out of byte range')
        return bytearray(f'{value:02x}', 'ascii')

    def delta(self, code, delta):
        level = self.query_data(code)
        return code[0:6] + self.hex_bytes_delta(level, delta)

    def increment(self, code):
        return self.delta(code, +1)

    def decrement(self, code):
        return self.delta(code, -1)

    def toggle(self, code, togglecommands):
        level = self.query_data(code)
        toggledata = (togglecommands[0][-2:], togglecommands[1][-2:])
        data = toggledata[0]
        if level == toggledata[0]:
            data = toggledata[1]
        return code[0:6] + data

    def send(self, command, data_arg=None):
        if command in self.debounces:
            wait_secs = self.debounces[command]
            if self.connection == None:
                self.connection = self.get_port()
            lock_path = os.path.join(tempfile.gettempdir(), '.' + command + '_lock')
            with FileLock(lock_path, timeout=0) as lock:
                response = self.query(command, data_arg)
                time.sleep(wait_secs)
        else:
            if self.connection == None:
                self.connection = self.get_port_ensured()
            response = self.query(command, data_arg)
        self.connection.close()
        self.connection = None # Serial might complain the port doesn't exist
        if isinstance(response, bytes):
            response = self.data_to_int(response)
            if command == 'inputstatus':
                try:
                    return self.inputs_by_data[response]
                except KeyError:
                    pass
        return response

    def available_commands(self):
        commands = self.codes.copy()
        commands.update(self.toggles)
        for command in commands.keys():
            code = commands[command]
            if command.endswith('level'):
                print("%s : %s" % (command[:-5] + 'up', code[:-2] + b'??'))
                print("%s : %s" % (command[:-5] + 'down', code[:-2] + b'??'))
            else:
                print("{0} : {1}".format(command, code))

    def add_toggle(self, command, state0, state1):
        self.toggles['toggle' + command] = (state0, state1)

    def debounce(self, command, wait_secs=0.5):
        self.debounces[command] = wait_secs


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('model', metavar='MODEL')
    parser.add_argument('-s', '--serial', metavar='SERIAL_DEVICE', default=LGTV.default_serial)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('-l', '--list-commands', action='store_true')
    action.add_argument('-c', '--command', metavar='COMMAND')
    parser.add_argument('-d', '--data', metavar='DATA')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    tv = LGTV(args.model, args.serial, args.verbose)
    if args.list_commands:
        tv.available_commands()
    elif args.command:
        data = args.data
        if data is not None:
            data = int(data)
        response = tv.send(args.command, data)
        if isinstance(response, int):
            print(hex(response))
        else:
            print(response)
        if response is None:
            sys.exit('TV rejected the command')


if __name__ == '__main__':
    main()
