import board
import time
import busio
import gc
import board
import neopixel
import rotaryio
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer

class Types:
    NUMBER_INPUT = "no"
    TEXT_INPUT = "text"

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

class ControllerConfig():
    
    def __init__(self, name, min_val=0, max_val=127,turns=1.0,init_value=0,
                 controller_value = 0, background_col = Col.BLUE,
                 val_col = Col.RED):
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        self.turns = turns
        self.encoder_value = 0
        self.init_value = init_value
        self.controller_value = init_value
        self.val_col = val_col
        self.background_col = background_col
 
class SerialControllerConfig(ControllerConfig):
    
    def __init__(self, name, min_val=0, max_val=127,turns=1.5,init_value=0,
                 controller_value = 0, background_col = Col.BLUE,
                 val_col = Col.RED, serial_port = None, serial_channel=1,pixel_start=0,no_of_pixels=8, stride=-8):
        super(SerialControllerConfig,self).__init__(
            name, min_val, max_val,turns,init_value,
                 controller_value, background_col,
                 val_col)
        self.serial_port = serial_port
        self.serial_channel = serial_channel
        self.pixel_start = pixel_start
        self.no_of_pixels = no_of_pixels
        self.stride = stride

class Controller():
    def __init__(self, client, name, encoder_pin1, encoder_pin2, pulses_rev,
                 button_pin, forward, configs, cursor_col = Col.WHITE
                 ):
        self.name = name
        self.client =  client
        self.screen_manager = client.screen_manager
        self.encoder= rotaryio.IncrementalEncoder(encoder_pin1, encoder_pin2)
        self.pulses_rev = pulses_rev
        self.last_encoder_position = 0
        tmp_pin = DigitalInOut(button_pin)
        tmp_pin.pull = Pull.UP
        self.button_debounce = Debouncer(tmp_pin,interval=0.01)
        self.activate_display()
        self.forward = forward
        self.first_run = True
        self.cursor_col = cursor_col
        self.configs = configs
        self.active_config_no = 0
        self.active_config = configs[0]
    
    def activate_display(self):
        self.encoder_display_time_end = time.monotonic() + 2

    def display_active(self):
        if time.monotonic() < self.encoder_display_time_end :
            return True
        else:
            return False

    def set_range(self,min_val,max_val,turns,pulses_rev):
        self.min = min_val
        self.max = max_val
        self.turns = turns
        
    def set_pixel_col(self,pixel_number,new_col):
        if self.screen_manager.pixels[pixel_number] != new_col:
            self.screen_manager.pixels[pixel_number] = new_col
            self.screen_manager.controls_active = True
        
    def draw_cursor(self):
        for config in self.configs:
            pixels = config.no_of_pixels
            stride = config.stride
            pulse_limit = int(self.pulses_rev * config.turns)-1
            turn_amount = config.encoder_value / pulse_limit
            cursor = int((pixels-1)*turn_amount)
            pos=0
            pix = config.pixel_start
            while pos < pixels:
                if pos<=cursor:
                    if pos == cursor:
                        if config == self.active_config:
                            self.set_pixel_col(pix, self.cursor_col)
                        else:
                            self.set_pixel_col(pix, config.val_col)
                    else:
                        self.set_pixel_col(pix, config.val_col)
                else:
                    self.set_pixel_col(pix, config.background_col)
                pos = pos + 1
                pix = pix + stride
            
    def update_encoder(self):
        new_encoder_position = self.encoder.position
        encoder_change = self.last_encoder_position - new_encoder_position
        
        if encoder_change != 0 or self.first_run:
            self.activate_display()
            if self.forward:
                new_pos = self.active_config.encoder_value - encoder_change
            else:
                new_pos = self.active_config.encoder_value + encoder_change
                
            if new_pos<0:
                new_pos=0
                
            pulse_limit = int(self.pulses_rev * self.active_config.turns)-1
            
            if new_pos>=pulse_limit:
                new_pos=pulse_limit
                 
            if self.active_config.encoder_value != new_pos or self.first_run:
                self.first_run = False
                self.active_config.encoder_value = new_pos
                turn_amount = new_pos / pulse_limit
                val_range = self.active_config.max_val - self.active_config.min_val
                scaled_change = turn_amount * val_range
                self.active_config.controller_value=scaled_change
                self.encoder_changed()
       
        self.last_encoder_position = new_encoder_position
        
    def update(self):
        self.button_debounce.update()
        if self.button_debounce.fell:
            self.activate_display()
            self.button_down()
        if self.button_debounce.rose:
            self.button_up()
        self.update_encoder()

    def draw(self):
        if self.display_active():
            self.draw_cursor()
            return True
        else:
            return False

    def reset(self):
        self.count=0
        
    def step_controller(self):
        self.active_config_no = (self.active_config_no + 1) % len(self.configs)
        self.active_config = self.configs[self.active_config_no]
        self.draw_cursor()
    
    def button_down(self):
        self.step_controller()
        
    def button_up(self):
        pass


class SerialController(Controller):
    
    def __init__(self, client, name, encoder_pin1, encoder_pin2, pulses_rev,
                 button_pin, forward, configs):
        super(SerialController,self).__init__(client = client, name = name,
                 encoder_pin1 = encoder_pin1, encoder_pin2 = encoder_pin2,
                 pulses_rev = pulses_rev, button_pin = button_pin,
                 forward = forward,
                 configs=configs)
    
    def encoder_changed(self):
        print("Controller changed: ",self.active_config.controller_value,self.active_config.serial_channel)
        if self.client.serial_port != None:
            b1 = int(self.active_config.serial_channel)
            b2 = int(self.active_config.controller_value)
            message = "encoder " + str(b1) + " " + str(b2) + "\n"
            send_buffer = bytes(message,"ascii")
            print("Sending to serial:", send_buffer)
            self.client.serial_port.write(send_buffer)


class PixelManager():
    def __init__(self, pixels, pixel_no):
        self.pixel_no = pixel_no
        self.col = [0,0,0]
        self.deltas = [0,0,0]
        self.current_step=0
        self.no_of_steps=0
    
    def set_col(self,new_col):
        for i in range(0,3):
            self.col[i]=new_col[i]

    def update(self):
        if self.current_step < self.no_of_steps:
            for i in range(0,3):
                c = self.col[i] + self.deltas[i]
                if c<0:
                    c=0
                if c>255:
                    c=255
                self.col[i]=c
            self.current_step = self.current_step + 1

    def draw(self, pixels):
        pixels[self.pixel_no] = self.col

    def start_fade(self,target_col,no_of_steps):
        self.current_step = 0
        self.no_of_steps = no_of_steps
        if no_of_steps == 0:
            self.set_col(target_col)
        else:
            for i in range(0,3):
                self.deltas[i] = (target_col[i] - self.col[i]) / no_of_steps

class ScreenManager():

    font_5x3 = (
        (0, 0),         # 32 - 'Space'
        (23,),          # 33 - '!'
        (3, 0, 3),      # 34 - '"'
        (31, 10, 31),   # 35 - '#'
        (22, 31, 13),   # 36 - '$'
        (9, 4, 18),     # 37 - '%'
        (10, 21, 26),   # 38 - '&'
        (3,),           # 39
        (14, 17),       # 40 - '('
        (17, 14),       # 41 - ')'
        (10, 4, 10),    # 42 - '*'
        (4, 14, 4),     # 43 - '+'
        (16, 8),        # 44 - ','
        (4, 4, 4),      # 45 - '-'
        (16,),          # 46 - '.'
        (8, 4, 2),      # 47 - '/'
        (31, 17, 31),   # 48 - '0'
        (0, 31),        # 49 - '1'
        (29, 21, 23),   # 50 - '2'
        (17, 21, 31),   # 51 - '3'
        (7, 4, 31),     # 52 - '4'
        (23, 21, 29),   # 53 - '5'
        (31, 21, 29),   # 54 - '6'
        (1, 1, 31),     # 55 - '7'
        (31, 21, 31),   # 56 - '8'
        (23, 21, 31),   # 57 - '9'
        (10,),          # 58 - ':'
        (16, 10),       # 59 - ';'
        (4, 10, 17),    # 60 - '<'
        (10, 10, 10),   # 61 - '='
        (17, 10, 4),    # 62 - '>'
        (1, 21, 3),     # 63 - '?'
        (14, 21, 22),   # 64 - '@'
        (30, 5, 30),    # 65 - 'A'
        (31, 21, 10),   # 66 - 'B'
        (14, 17, 17),   # 67 - 'C'
        (31, 17, 14),   # 68 - 'D'
        (31, 21, 17),   # 69 - 'E'
        (31, 5, 1),     # 70 - 'F'
        (14, 17, 29),   # 71 - 'G'
        (31, 4, 31),    # 72 - 'H'
        (17, 31, 17),   # 73 - 'I'
        (8, 16, 15),    # 74 - 'J'
        (31, 4, 27),    # 75 - 'K'
        (31, 16, 16),   # 76 - 'L'
        (31, 2, 31),    # 77 - 'M'
        (31, 14, 31),   # 78 - 'N'
        (14, 17, 14),   # 79 - 'O'
        (31, 5, 2),     # 80 - 'P'
        (14, 25, 30),   # 81 - 'Q'
        (31, 5, 26),    # 82 - 'R'
        (18, 21, 9),    # 83 - 'S'
        (1, 31, 1),     # 84 - 'T'
        (15, 16, 15),   # 85 - 'U'
        (7, 24, 7),     # 86 - 'V'
        (15, 28, 15),   # 87 - 'W'
        (27, 4, 27),    # 88 - 'X'
        (3, 28, 3),     # 89 - 'Y'
        (25, 21, 19),   # 90 - 'Z'
        (31, 17),       # 91 - '['
        (2, 4, 8),      # 92 - '\'
        (17, 31),       # 93 - ']'
        (2, 1, 2),      # 94 - '^'
        (16, 16, 16),   # 95 - '_'
        (1, 2),         # 96 - '`'
        (12, 18, 28),   # 97 - 'a'
        (31, 18, 12),   # 98 - 'b'
        (12, 18, 18),   # 99 - 'c'
        (12, 18, 31),   # 100 - 'd'
        (12, 26, 20),   # 101 - 'e'
        (4, 31, 5),     # 102 - 'f'
        (20, 26, 12),   # 103 - 'g'
        (31, 2, 28),    # 104 - 'h'
        (29,),          # 105 - 'i'
        (16, 13),       # 106 - 'j'
        (31, 8, 20),    # 107 - 'k'
        (31,),          # 108 - 'l'
        (30, 6, 30),    # 109 - 'm'
        (30, 2, 28),    # 110 - 'n'
        (12, 18, 12),   # 111 - 'o'
        (30, 10, 4),    # 112 - 'p'
        (4, 10, 30),    # 113 - 'q'
        (30, 4),        # 114 - 'r'
        (20, 30, 10),   # 115 - 's'
        (4, 30, 4),     # 116 - 't'
        (14, 16, 30),   # 117 - 'u'
        (14, 16, 14),   # 118 - 'v'
        (14, 24, 14),   # 119 - 'w'
        (18, 12, 18),   # 120 - 'x'
        (22, 24, 14),   # 121 - 'y'
        (26, 30, 22),   # 122 - 'z'
        (4, 27, 17),    # 123 - '{'
        (27,),          # 124 - '|'
        (17, 27, 4),    # 125 - '}'
        (6, 2, 3),      # 126 - '~'
        (31, 31, 31) # 127 - 'Full Block'
    )

    def __init__(self, controller, gpio, width,height):
        self.controller = controller
        self.panel_width = width
        self.panel_height = height
        self.no_of_pixels = width*height
        self.pixels = neopixel.NeoPixel(gpio,self.no_of_pixels,auto_write=False)
        self.pixel_managers = []
        for i in range(0,self.no_of_pixels):
            self.pixel_managers.append(PixelManager(self.pixels,i))
        self.pixels.brightness = 0.3
        self.update_interval = 0.02
        self.draw_interval = 0.02
        self.controls_active = True
        self.next_update_time = time.monotonic() + self.update_interval
        self.next_draw_time = time.monotonic() + self.draw_interval
        self.control_display_end_time = time.monotonic() + 2
        self.start_text_display()

    # draw the text on the display taking into account scrolling

    def get_char_design(self,ch):
        ch_offset = ord(ch) - ord(' ')
        if ch_offset<0 or ch_offset>len(self.font_5x3):
            return None
        return self.font_5x3[ch_offset]
    
    def draw_text(self):

        if self.text == '':
            return

        x = self.text_x
        y = self.text_y

        ch_pos = self.text_char_pos
        column = self.text_char_column
        pixel_offset = x + (y*self.panel_width)

        while ch_pos < len(self.text):

            if pixel_offset >= self.no_of_pixels:
                return

            ch = self.text[ch_pos]

            char_design = self.get_char_design(ch)

            if char_design == None:
                return

            char_design_length = len(char_design)
            
            while column < char_design_length:
                if x >= self.panel_width:
                    return
                # display the character raster
                font_column =char_design[column]
                bit = 1
                draw_pixel = pixel_offset

                while(bit<32):
                    if draw_pixel >= self.no_of_pixels:
                        return

                    if font_column & bit:
                        self.pixels[draw_pixel] = self.text_colour

                    # move on to the next bit in the column
                    bit = bit + bit
                    # move onto the next pixel to draw
                    draw_pixel = draw_pixel + self.panel_width

                column = column + 1
                pixel_offset = pixel_offset + 1 
                x = x + 1

            # reached the end of displaying a character - move to the next one
            x = x + 1
            ch_pos = ch_pos + 1
            pixel_offset = pixel_offset + 1 
            column = 0

    def start_scroll(self):

        if len(self.text) == 0:
            return

        self.text_char_column = 0
        self.text_step=0

        ch = self.text[self.text_char_pos]

        self.text_char_design = self.get_char_design(ch)

    def scroll_text(self):

        if len(self.text) == 0:
            return

        self.text_char_column = self.text_char_column + 1

        if self.text_char_column >= len(self.text_char_design):
            self.text_char_pos = self.text_char_pos + 1
            if self.text_char_pos >= len(self.text):
                self.text_char_pos = 0
                if self.scroll_count >0:
                    self.scroll_count = self.scroll_count-1
                    if self.scroll_count <=0:
                        self.text='' 
                        return
            self.start_scroll()

    def update_text(self):

        if len(self.text) == 0:
            return

        self.text_step = self.text_step + 1

        if self.text_step >= self.text_step_limit:
            self.scroll_text()
            self.text_step = 0

    def start_text_display(self,text='',colour=Col.BLACK,steps=8000,x=0,y=0,scroll_count=1):

        # put some spaces on the front so the text scrolls in from the right
        self.text = '     ' + text
        self.text_colour = colour
        self.text_step_limit = steps
        self.text_x = x
        self.text_y = y

        self.text_step = 0
            
        self.scroll_count = scroll_count

        if len(self.text) == 0:
            return

        self.text_char_pos = 0

        self.start_scroll()

    def update(self, current_time ):
        if current_time >= self.next_update_time:
            self.next_update_time = current_time + self.update_interval

            for pixel in self.pixel_managers:
                pixel.update()

            self.update_text()

    # returns True if the display is dirty and must be updated
    def draw(self,current_time):

        if current_time < self.next_draw_time :
            return False
        else:
            self.next_draw_time = current_time + self.draw_interval
            for pixel in self.pixel_managers:
                pixel.draw(self.pixels)
            self.draw_text()
            return True

class ScreenCommand():

    def get_pixel_offset(self,x,y):
        return y*self.width + x

    def __init__(self, controller):
        self.controller = controller
        self.mgr = controller.screen_manager
        self.width = controller.screen_manager.panel_width
        self.height = controller.screen_manager.panel_height
 
    def process_command(self):
        result = []
        con = self.controller

        for default_item in self.defaults:
            if (con.packet_buffer_read==con.packet_buffer_pos) or (con.packet_input_buffer[con.packet_buffer_read] == ';'):
                # end of the buffer - add the default
                result.append(default_item[1])
            else:
                # read an item
                command_item = con.get_next_packet_item()
                if command_item == None:
                    result.append(default_item[1])
                else:
                    # make sure it is the right type
                    if command_item[0] != default_item[0]:
                        result.append(default_item[1])
                    result.append(command_item[1])
        return result


# Draw blocks all in the same colour
class C_0_DrawBlock(ScreenCommand):

    def __init__(self,controller):
        super(C_0_DrawBlock,self).__init__(controller)

        self.defaults = ( 
            (Types.NUMBER_INPUT,0),           # 0 red
            (Types.NUMBER_INPUT,0),           # 1 green
            (Types.NUMBER_INPUT,0),           # 2 blue
            (Types.NUMBER_INPUT,5),           # 3 steps
            (Types.NUMBER_INPUT,0),           # 4 x
            (Types.NUMBER_INPUT,0),           # 5 y
            (Types.NUMBER_INPUT,self.width),  # 6 width
            (Types.NUMBER_INPUT,self.height)  # 7 height
        )
            
        self.current_step=0
        self.no_of_steps=0

    def process_command(self):

        com = super(C_0_DrawBlock,self).process_command()

        if com == None:
            return

        target = (com[0],com[1],com[2])

        steps = com[3]
        x = com[4]
        y = com[5]
        w = com[6]
        h = com[7]
        for yp in range(0,h):
            fy = y + yp
            if fy < self.height:
                for xp in range (0,w):
                    fx = x + xp
                    if fx < self.width:
                        pix_no = self.get_pixel_offset(fx,fy)
                        self.mgr.pixel_managers[pix_no].start_fade(target,steps) 

# Draw dots at positions on the screen all of the same colour
class C_1_Drawdot(ScreenCommand):

    def __init__(self,controller):
        super(C_1_Drawdot,self).__init__(controller)
        self.defaults = ( 
            (Types.NUMBER_INPUT,0),           # 0 red
            (Types.NUMBER_INPUT,0),           # 1 green
            (Types.NUMBER_INPUT,0),           # 2 blue
            (Types.NUMBER_INPUT,5),           # 3 steps
            (Types.NUMBER_INPUT,0),           # 4 x
            (Types.NUMBER_INPUT,0)            # 5 y
        )
            
        self.current_step=0
        self.no_of_steps=0

    def process_command(self):
        com = super(C_1_Drawdot,self).process_command()

        if com == None:
            return

        target = (com[0],com[1],com[2])

        steps = com[3]
        x = com[4]
        y = com[5]
        pix_no = self.get_pixel_offset(x,y)
        if pix_no < len(self.mgr.pixel_managers):
            self.mgr.pixel_managers[pix_no].start_fade(target,steps)

class C_2_DrawText(ScreenCommand):
    def __init__(self,controller):
        super(C_2_DrawText,self).__init__(controller)
        self.defaults = ( 
            (Types.NUMBER_INPUT,0),           # 0 red
            (Types.NUMBER_INPUT,0),           # 1 green
            (Types.NUMBER_INPUT,0),           # 2 blue
            (Types.NUMBER_INPUT,5),           # 3 steps
            (Types.NUMBER_INPUT,0),           # 4 x
            (Types.NUMBER_INPUT,0),           # 5 y
            (Types.TEXT_INPUT,"hello world"), # 6 text
            (Types.NUMBER_INPUT,0)            # 7 repeat scroll
        )
            
        self.current_step=0
        self.no_of_steps=0

    def process_command(self):
        com = super(C_2_DrawText,self).process_command()

        if com == None:
            return

        colour = (com[0],com[1],com[2])

        steps = com[ 3]
        x = com[4]
        y = com[5]
        text = com[6]
        scroll = com[7]

        self.mgr.start_text_display(text,colour,steps,x,y,scroll)

class C_3_SetCtrl(ScreenCommand):
    def __init__(self,controller):
        super(C_3_SetCtrl,self).__init__(controller)
        self.defaults = ( 
            (Types.NUMBER_INPUT,0),           # 0 ctrl
            (Types.NUMBER_INPUT,0),           # 1 value
        )

    def process_command(self):
        com = super(C_3_SetCtrl,self).process_command()

        if com == None:
            return

        ctrl_no = com[0]
        value = com[1]
        print("CtrlL",ctrl_no,"Value:",value)
        
        result = controller.find_serial_controller_by_number(ctrl_no)

        if result==None:
            return
        
        (serial_controller,config) = result

        print("Controller: ",config.name)

class DisplayController():

    def __init__(self):
        print("Rob Miles Chocolate Synthbox Interface 1.0")
        #                          TX         RX
        self.serial_port = busio.UART(board.GP8, board.GP9, baudrate=19200,receiver_buffer_size=500)
        self.screen_manager = ScreenManager(self,board.GP18,8,8)

        base = 0
        c1 = [
            SerialControllerConfig("c1", serial_port=self.serial_port, serial_channel=base+1,pixel_start=56,min_val=1, max_val=8),
            SerialControllerConfig("c2", serial_port=self.serial_port, serial_channel=base+2, background_col = Col.YELLOW, pixel_start=57),
            SerialControllerConfig("c3", serial_port=self.serial_port, serial_channel=base+3, background_col = Col.GREEN, pixel_start=58),
            SerialControllerConfig("c4", serial_port=self.serial_port, serial_channel=base+4, background_col = Col.MAGENTA, pixel_start=59)
            ]
        
        c2 = [
            SerialControllerConfig("c5", serial_port=self.serial_port,serial_channel=base+5,pixel_start=63),
            SerialControllerConfig("c6", serial_port=self.serial_port,serial_channel=base+6, background_col = Col.YELLOW, pixel_start=62),
            SerialControllerConfig("c7", serial_port=self.serial_port,serial_channel=base+7, background_col = Col.GREEN, pixel_start=61),
            SerialControllerConfig("c8", serial_port=self.serial_port,serial_channel=base+8, background_col = Col.MAGENTA, pixel_start=60)
            ]
    
        self.serial_controllers = [
            SerialController(client=self, name="c1", encoder_pin1=board.GP13, encoder_pin2=board.GP12, pulses_rev=20,
                           button_pin=board.GP16, forward=False, configs=c1),
            SerialController(client=self, name="c2", encoder_pin1=board.GP11, encoder_pin2=board.GP10, pulses_rev=20,
                           button_pin=board.GP17, forward=False,  configs=c2)
            ]

        self.setup_command_input()

    def find_serial_controller_by_number(self, controller_no):
        controller_count = 1
        for controller in self.serial_controllers:
            for config in controller.configs:
                if controller_no == controller_count:
                    return (controller, config)
                controller_count = controller_count + 1
        return None

    def button_down(self,controller):
        pass
        
    def button_up(self,controller):
        pass

    def encoder_changed(self, controller, change):
        pass

    def process_incoming_packetx(self):
        command_number = self.packet_input_buffer[0]
        command_processor = self.command_processors[command_number-1]
        command_processor.process_command()

    def setup_command_input(self,packet_buffer_length=256):
        # setup the command decoder
        self.command_processors = [
            C_0_DrawBlock(self),   
            C_1_Drawdot(self),
            C_2_DrawText(self),
            C_3_SetCtrl(self)
        ]

        # build the fixed length packet input buffer
        self.packet_input_buffer = []
        for i in range(0,packet_buffer_length):
            self.packet_input_buffer.append(0)
        self.packet_buffer_length = packet_buffer_length
        self.packet_buffer_pos=0
        self.packet_buffer_read=0
        self.command_changed_display = False

    def get_next_packet_item(self):

        if self.packet_buffer_read==self.packet_buffer_pos:
            return None

        if self.packet_input_buffer[self.packet_buffer_read] == ';':
            return None

        # skip leading spaces

        while(self.packet_input_buffer[self.packet_buffer_read] == ' '):
            self.packet_buffer_read = self.packet_buffer_read + 1
            if self.packet_buffer_read == self.packet_buffer_pos:
                return None

        if self.packet_input_buffer[self.packet_buffer_read].isdigit():
            # reading a number
            result=0
            while self.packet_input_buffer[self.packet_buffer_read].isdigit():
                digit = ord(self.packet_input_buffer[self.packet_buffer_read]) - ord('0')
                result = result * 10 + digit
                self.packet_buffer_read = self.packet_buffer_read + 1
                if self.packet_buffer_read == self.packet_buffer_pos:
                    return None
            return (Types.NUMBER_INPUT, result)

        if self.packet_input_buffer[self.packet_buffer_read] == "'":
            # reading a string
            self.packet_buffer_read = self.packet_buffer_read + 1
            if self.packet_buffer_read == self.packet_buffer_pos:
                return None
            result = ""            
            while self.packet_input_buffer[self.packet_buffer_read] != "'":
                ch = self.packet_input_buffer[self.packet_buffer_read]
                result = result + ch
                self.packet_buffer_read = self.packet_buffer_read + 1
                if self.packet_buffer_read == self.packet_buffer_pos:
                    return None
            self.packet_buffer_read = self.packet_buffer_read+1
            return (Types.TEXT_INPUT, result)
        return None

    def process_incoming_packet(self):
        print("Processing:",end="")

        for i in range(0,self.packet_buffer_pos):
            print(self.packet_input_buffer[i],end="")

        print()

        prefix = "list "
        pos = 0
        limit = self.packet_buffer_pos
        for test_char in prefix:
            if pos == limit:
                # incoming packet too small
                return "incoming packet too small"
            if test_char != self.packet_input_buffer[pos]:
                # invalid message start
                return "invalid packet start"
            pos = pos + 1

        self.packet_buffer_read = len(prefix)

        command_item = self.get_next_packet_item()

        if command_item[0] != Types.NUMBER_INPUT:
            return "no command number"

        command_number = command_item[1]

        if command_number >= len(self.command_processors) or command_number <0:
            return "invalid command number"

        return self.command_processors[command_number].process_command()

    def process_incoming_byte(self,b):
        separator = 10
        # If we get a separator we might have a command packet
        if b == separator:
            # Make sure we have a command to process
            if self.packet_buffer_pos > 0:
                reply = self.process_incoming_packet()
                if reply != None:
                    print(reply)
                # reset the buffer
                self.packet_buffer_pos = 0
        else:
            # add the byte to the buffer
            if self.packet_buffer_pos == self.packet_buffer_length:
                # If the packet is too long - discard it and wait for the next one
                # reset the buffer
                self.packet_buffer_pos = 0
            else:
                # Store the byte and update the position
                self.packet_input_buffer[self.packet_buffer_pos] = chr(b)
                self.packet_buffer_pos = self.packet_buffer_pos + 1

    def process_incoming_bytes(self,bytes):
        for b in bytes:
            self.process_incoming_byte(b)

    def process_command_string(self,str):
        for ch in str:
            self.process_incoming_byte(ord(ch))
        self.process_incoming_byte(10)

    def update(self):
        incoming_bytes = self.serial_port.in_waiting
        if incoming_bytes != 0:
            serial_bytes = self.serial_port.read(incoming_bytes)
            self.process_incoming_bytes(serial_bytes)

        current_time = time.monotonic()

        self.screen_manager.update(current_time)
        for controller in self.serial_controllers:
            controller.update()

        display_dirty = False

        if self.screen_manager.draw(current_time):
            display_dirty = True

        for controller in self.serial_controllers:
            if controller.draw():
                display_dirty = True
        
        if display_dirty:
            self.screen_manager.pixels.show()

controller = DisplayController()

controller.process_command_string("list 2 255 255 0 8 0 0 '    hello world' 1;")


while True:
    controller.update()    
