#!/usr/bin/env python

import serial
import signal
import sys
import time
import re
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

def setup_serial_ports():

    port_in = serial.Serial(port=cfg.port_in,
                            baudrate= cfg.port_in_baud,
                            timeout=0.0)
	
    port_out = serial.Serial(port=cfg.port_out,
                            baudrate= cfg.port_out_baud,
                            timeout=0.0)
    
    port_in.flush()
    port_out.flush()

    dm.print_info("Serial port ready")
    return port_in, port_out

def send_vehicle_commands(old_steering, old_throttle, steering, throttle, port):
    """
        Sends steering and throttle to the kart 
    
	Steering: Full CC - CW
		(180 - 0)
	Throttle: Dead - Full - Brake
		(92 - 180 - <90)
		 
    """
    # dm.print_info("S: {} T: {}".format(steering, throttle))
    # Steering
    if old_steering != steering:
        steering_out = ('S%d\n' % int(steering)).encode('ascii')
        port.write(steering_out)

    # Clamp throttle
    if old_throttle != throttle:
        if 88 <= throttle <= 92:
            throttle = 90
        else:
            throttle = min(throttle, 110)
          
        throttle_out = ('D%d\n' % int(throttle)).encode('ascii')
	port.write(throttle_out)
    port.flush()

buffer_in =''
buffer_out = ''
button_arduino_in = 0
button_arduino_out = 0
odometer_ticks=0
def process_input(port_in, port_out):
	"""Reads steering, throttle, aux1 and button data reported from the arduinos.
	Returns: (steering, throttle, button_arduino_in, button_arduino_out)
	Return values may be None if the data from the arduino isn't related to the
	steering or throttle.
	"""
	# Input is buffered because sometimes partial lines are read
	global button_arduino_in, button_arduino_out, buffer_in, buffer_out, odometer_ticks, milliseconds
	try:
		buffer_in += port_in.read(port_in.in_waiting).decode('ascii')
		buffer_out += port_out.read(port_out.in_waiting).decode('ascii')
	except UnicodeDecodeError:
		# We can rarely get bad data over the serial port. The error looks like this:
		# buffer_in += port_in.read(port_in.in_waiting).decode('ascii')
		# UnicodeDecodeError: 'ascii' codec can't decode byte 0xf0 in position 0: ordinal not in range(128)
		buffer_in = ''
		buffer_out = ''
		dm.print_warning("Mysterious serial port error. Let's pretend it didn't happen. :)")
	# Init steering, throttle and aux1.
	steering, throttle, aux1 = None, None, None
	# Read lines from input Arduino
	while '\n' in buffer_in:
		line, buffer_in = buffer_in.split('\n', 1)
		match = re.search(r'(\d+) (\d+) (\d+)', line)
		
		if match:
			steering = int(match.group(1))
			throttle = int(match.group(2))
			aux1 = int(match.group(3))
		if line[0:1] == 'S':
			# This is just a toggle button
			button_arduino_in = 1 - button_arduino_in
	# Read lines from output Arduino
	while '\n' in buffer_out:
		line, buffer_out = buffer_out.split('\n', 1)
		if line[0:3] == 'Mil':
			sp = line.split('\t')
			milliseconds = int(sp[1])
			odometer_ticks += 1
		if line[0:6] == 'Button':
			sp = line.split('\t')
			button_arduino_out = int(sp[1])
	return steering, throttle, aux1, button_arduino_in, button_arduino_out

def main():
    dm.print_info("Starting carputer passthrough")

    dm.print_info("Setting up serial ports")

    port_in, port_out = setup_serial_ports()

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
        new_steering, new_throttle, new_aux, b1, b2 = process_input(port_in, port_out)

        # Check for valid input
        if new_steering != None:
            steering = new_steering
        if new_throttle != None:
            throttle = new_throttle
        if new_aux != None:
            aux = new_aux
        
        dm.print_debug("S: {}, T: {}, aux: {}".format(steering, throttle, aux))

        # Simple passthrough
        send_vehicle_commands(steering_old, throttle_old, steering, throttle, port_out)

        # Update the values
        aux_old = aux
        steering_old = steering
        throttle_old = throttle

        # Rate limit so we aren't destroying the CPU
        rate_limit(start, 0.001)


if __name__ == "__main__":
    main()
