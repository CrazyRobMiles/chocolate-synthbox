import board
import busio
import time
import gc
import board
import neopixel
import rotaryio
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer

import binascii

#                       TX         RX
uart = busio.UART(board.GP8, board.GP9, baudrate=115200)
#uart = busio.UART(tx=board.GP4, rx=board.GP5, baudrate=115200)
buffer = (1,2,3)
x = bytes(buffer)
uart.write(x)

while True:
    b = uart.read(1)
    if b!= None:
#         if len(b)==1:
#             if b[0]==0:
#                 continue
        print(b)
    time.sleep(0.1)