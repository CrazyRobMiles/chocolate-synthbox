import board
import busio
import time
import gc
import board
import neopixel
import rotaryio
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer

class Col:
    
    RED = (255, 0, 0)
    YELLOW = (255, 150, 0)
    GREEN = (0, 255, 0)
    CYAN = (0, 255, 255)
    BLUE = (0, 0, 255)
    MAGENTA = (255, 0, 255)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREY = (10, 10, 10)
    VIOLET = (127,0,155)
    INDIGO = (75,0,130)
    ORANGE = (255,165,0)
       
    values=(RED, GREEN, BLUE, YELLOW, MAGENTA, CYAN, GREY, WHITE)
    
   
    @staticmethod
    def dim(col):
        return (col[0]/40, col[1]/40, col[2]/40)

pixels = neopixel.NeoPixel(board.GP18,64,auto_write=False)
pixels.brightness = 0.5
delay_time = 2
pixels[0]=Col.RED
pixels[1]=Col.GREEN
pixels[2]=Col.BLUE
pixels.show()

