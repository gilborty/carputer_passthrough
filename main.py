#!/usr/bin/env python

import serial
import signal
import sys
import time

import config as cfg

# Pretty print for debug messages
from debug_message import DebugMessage
dm = DebugMessage(enable_logging=True, logging_file="./.carputer_passthrough.log")

is_running = True
def signal_handler(*args):
    dm.print_warning("SIGINT detected, closing...")
    global is_running
    is_running = False
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Helper for rate limiting
def rate_limit(start, rate=0.5):
    end = time.time()
    delta = end - start
    sleep_for = rate - delta

    if sleep_for > delta:
        time.sleep(sleep_for)

def setup_serial_port():

    dm.print_info("Using serial port {}".format(cfg.serial_port_name))
    dm.print_info("With baudrate {}".format(cfg.serial_port_baudrate))

    try:
        port = serial.Serial(port=cfg.serial_port_name,
                            baudrate= cfg.serial_port_baudrate,
                            timeout=0.0)
    
    except:
        dm.print_fatal("Could not open serial port {} with baudrate {}".format(cfg.serial_port_name, cfg.serial_port_baudrate))
        sys.exit(-1)
        
    port.flush()

    dm.print_info("Serial port ready")
    return port

def main():
    dm.print_info("Starting carputer passthrough")

    dm.print_info("Setting up serial ports")

    serial_port = setup_serial_port()

    global is_running
    while is_running:

        start = time.time()

        # Get the commanded input from the arduino



        # Rate limit so we aren't destroying the CPU
        rate_limit(start, 0.001)




if __name__ == "__main__":
    main()