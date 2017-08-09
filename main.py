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

def send_vehicle_commands(old_steering, old_throttle, steering, throttle, port):
    """
        Sends steering and throttle to the kart 
    """
    # Steering
    if old_steering != steering:
        steering_out = ('S%d\n' % steering).encode('ascii')
        port.write(steering_out)
        dm.print_warning("Write one {}".format(steering_out))

    # Clamp throttle
    if old_throttle != throttle:
        if 88 <= throttle <= 92:
            throttle = 90
        else:
            throttle = min(throttle, 110)
          
        throttle_out = ('D%d\n' % throttle).encode('ascii')
        port.write(throttle_out)
        dm.print_warning("Write two {}".format(throttle_out))
    port.flush()


def main():
    dm.print_info("Starting carputer passthrough")

    dm.print_info("Setting up serial ports")

    serial_port = setup_serial_port()

    # Init values
    steering = 0
    steering_old = 0

    throttle = 0
    throttle_old = 0

    aux = 0
    aux_old = 1000


    global is_running
    while is_running:

        start = time.time()

        # Get the commanded input from the arduino
        new_steering, new_throttle, new_aux = process_inputs(steering, throttle, aux, serial_port)

        # Check for valid input
        if new_steering != None:
            steering = new_steering
        if new_throttle != None:
            throttle = new_throttle
        if new_aux != None:
            aux - new_aux
        
        dm.print_debug("S: {}, T: {}, aux: {}".format(steering, throttle, aux))

        # Simple passthrough
        send_vehicle_commands(steering_old, throttle_old, steering, throttle, serial_port)

        # Update the values
        aux_old = aux
        steering_old = steering
        throttle_old = throttle

        # Rate limit so we aren't destroying the CPU
        rate_limit(start, 0.001)


if __name__ == "__main__":
    main()