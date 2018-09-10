#!/usr/bin/env python3

from math import ceil, log2
from optparse import OptionParser
import Adafruit_GPIO as GPIO
import Adafruit_GPIO.I2C as I2C
import Adafruit_GPIO.MCP230xx as MCP230xx


class RPi_Switcher(object):

    MAX_MCPS = 8
    NUM_RPIS_PER_MCP = 4
    MCP_ADDR_BASE = 0x20

    class MCP(MCP230xx.MCP23008):

        POWER_PINS = [0, 1, 5, 6]
        SERIAL_EN_PIN = 2
        SERIAL_MUX_PINS = [3, 4]

        def print(self, *args):
            print('0x%02x:' % self.address, *args)

        def __init__(self, address, NUM_RPIS_PER_MCP, verbose=False,
                dry_run=False):
            self.address = address
            self.NUM_RPIS_PER_MCP = NUM_RPIS_PER_MCP
            self.verbose = verbose
            self.dry_run = dry_run

            assert(len(self.POWER_PINS) == self.NUM_RPIS_PER_MCP)
            assert(len(self.SERIAL_MUX_PINS) ==
                    int(ceil(log2(self.NUM_RPIS_PER_MCP))))

            if self.dry_run:
                if self.verbose:
                    self.print('Inited with dry-run mode')
                return

            self._device = I2C.get_i2c_device(address)

            self.gpio_bytes = int(ceil(self.NUM_GPIO / 8.0))
            if verbose:
                self.print('gpio_bytes =', self.gpio_bytes)

            old_iodir = self._device.readList(self.IODIR, self.gpio_bytes)
            if verbose:
                self.print('old_iodir =', old_iodir)

            # GPPU: 0=pullup disabled, 1=pullup enabled
            self.gppu = [0x00] * self.gpio_bytes
            self.write_gppu()
            # IODIR is initialized to all 0xff on reset.
            if not all(x == 0x00 for x in old_iodir):
                # Initial run.
                # GPIO: 0=LOW, 1=HIGH
                if verbose:
                    self.print('Initializing GPIO reg to all zero')
                self.gpio = [0x00] * self.gpio_bytes
                self.write_gpio()
            else:
                # Read the current state.
                if verbose:
                    self.print('Using the current value of GPIO reg')
                self.gpio = self._device.readList(self.GPIO, self.gpio_bytes)
                if verbose:
                    self.print('Current GPIO:', self.gpio)
            # IODIR: 0=output, 1=input
            self.iodir = [0x00] * self.gpio_bytes
            self.write_iodir()

        def set_power(self, n, power):
            assert(0 <= n < self.NUM_RPIS_PER_MCP)
            if self.verbose:
                self.print('Setting power of RPi', n, 'to',
                        'on' if power else 'off')
            if not self.dry_run:
                self.output(self.POWER_PINS[n],
                        GPIO.HIGH if power else GPIO.LOW)

        def enable_serial(self, stat):
            if self.verbose:
                self.print('Enabling' if stat else 'Disabling', 'serial')
            if not self.dry_run:
                self.output(self.SERIAL_EN_PIN, GPIO.HIGH if stat else GPIO.LOW)

        def select_serial(self, n):
            assert(0 <= n < self.NUM_RPIS_PER_MCP)
            d = {}
            for i in range(len(self.SERIAL_MUX_PINS)):
                pin = self.SERIAL_MUX_PINS[i]
                if n & (1 << i):
                    d[pin] = GPIO.HIGH
                else:
                    d[pin] = GPIO.LOW
            if self.verbose:
                self.print('select_serial: Writing', d)
            if not self.dry_run:
                self.output_pins(d)

        def get_status_of_pin(self, pin):
            assert(pin < self.gpio_bytes * 8)
            return bool(self.gpio[pin // 8] & (1 << (pin % 8)))

        def get_power(self, n):
            assert(0 <= n < self.NUM_RPIS_PER_MCP)
            return self.get_status_of_pin(self.POWER_PINS[n])

        def get_serial(self):
            if not self.get_status_of_pin(self.SERIAL_EN_PIN):
                return -1
            mux = 0
            for i in range(len(self.SERIAL_MUX_PINS)):
                mux |= self.get_status_of_pin(self.SERIAL_MUX_PINS[i]) << i
            return mux


    def __init__(self, verbose=False, dry_run=False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.mcps = [None for i in range(self.MAX_MCPS)]

    def init_mcp_of_slave(self, n):
        n //= self.NUM_RPIS_PER_MCP
        if self.mcps[n] is not None:
            return self.mcps[n]
        addr = self.MCP_ADDR_BASE + n
        mcp = self.MCP(address=addr, NUM_RPIS_PER_MCP=self.NUM_RPIS_PER_MCP,
                verbose=self.verbose, dry_run=self.dry_run)
        self.mcps[n] = mcp
        return mcp

    def init_all_mcps(self):
        for i in range(self.MAX_MCPS):
            try:
                mcp = self.init_mcp_of_slave(self.NUM_RPIS_PER_MCP * i)
            except OSError:
                pass

    def set_power(self, n, power):
        mcp = self.init_mcp_of_slave(n)
        mcp.set_power(n % self.NUM_RPIS_PER_MCP, power)

    def get_power(self, n):
        try:
            mcp = self.init_mcp_of_slave(n)
        except OSError:
            return False
        return mcp.get_power(n % self.NUM_RPIS_PER_MCP)

    def select_serial(self, n):
        self.init_all_mcps()

        if n >= 0:
            mcp_idx = n // self.NUM_RPIS_PER_MCP
            if self.mcps[mcp_idx] is None:
                raise IOError('MCP device %d ' % mcp_idx +
                        'which corresponds to slave %d is not found' % n)

        for mcp in self.mcps:
            if mcp is not None:
                mcp.enable_serial(False)

        if n >= 0:
            self.mcps[mcp_idx].select_serial(n % self.NUM_RPIS_PER_MCP)
            self.mcps[mcp_idx].enable_serial(True)

    def get_serial(self):
        self.init_all_mcps()
        for i in range(len(self.mcps)):
            mcp = self.mcps[i]
            if mcp is not None:
                stat = mcp.get_serial()
                if stat >= 0:
                    return self.NUM_RPIS_PER_MCP * i + stat
        return -1


def main():
    parser = OptionParser()

    parser.add_option('-v', '--verbose',
            action='store_true', dest='verbose', default=False,
            help='Be verbose (default: no)')
    parser.add_option('-D', '--dry-run',
            action='store_true', dest='dry_run', default=False,
            help='Dry-run mode (default: no)')
    parser.add_option('-d', '--off',
            action='append', type='int', dest='off',
            help='RPi no. to turn off')
    parser.add_option('-e', '--on',
            action='append', type='int', dest='on',
            help='RPi no. to turn on')
    parser.add_option('-s', '--serial',
            action='store', type='int', dest='serial',
            help='RPi no. to connect serial to')
    parser.add_option('-i', '--info',
            action='append', type='str', dest='info',
            help='RPi no. or "s" (serial) to check its status')

    (options, args) = parser.parse_args()
    if len(args) != 0:
        parser.error('Extra arguments specified')

    if options.on is None and \
            options.off is None and \
            options.serial is None and \
            options.info is None:
        parser.print_help()
        return

    sw = RPi_Switcher(verbose=options.verbose, dry_run=options.dry_run)

    if options.off is not None:
        for n in options.off:
            sw.set_power(n, GPIO.LOW)
    if options.on is not None:
        for n in options.on:
            sw.set_power(n, GPIO.HIGH)
    if options.serial is not None:
        sw.select_serial(options.serial)

    if options.info is not None:
        for s in options.info:
            if s == "s":
                print(sw.get_serial())
            else:
                n = int(s, base=0)
                print(int(sw.get_power(n)))


if __name__ == '__main__':
    main()
