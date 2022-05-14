import board
import time
import busio
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

class ControllerConfig():
    
    def __init__(self, min_val=0, max_val=127,turns=1.0,init_value=0,
                 controller_value = 0, background_col = Col.BLUE,
                 val_col = Col.RED):
        self.min_val = min_val
        self.max_val = max_val
        self.turns = turns
        self.encoder_value = 0
        self.init_value = init_value
        self.controller_value = init_value
        self.val_col = val_col
        self.background_col = background_col
 
class SerialControllerConfig(ControllerConfig):
    
    def __init__(self, min_val=0, max_val=127,turns=1.0,init_value=0,
                 controller_value = 0, background_col = Col.BLUE,
                 val_col = Col.RED, serial_port = None, serial_channel=1,pixel_start=0,no_of_pixels=8):
        super(SerialControllerConfig,self).__init__(
            min_val, max_val,turns,init_value,
                 controller_value, background_col,
                 val_col)
        self.serial_port = serial_port
        self.serial_channel = serial_channel
        self.pixel_start = pixel_start
        self.no_of_pixels = no_of_pixels

class Controller():
    def __init__(self, client, name, encoder_pin1, encoder_pin2, pulses_rev,
                 button_pin, forward, configs, cursor_col = Col.WHITE
                 ):
        self.name = name
        self.client =  client
        self.encoder= rotaryio.IncrementalEncoder(encoder_pin1, encoder_pin2)
        self.pulses_rev = pulses_rev
        self.last_encoder_position = 0
        tmp_pin = DigitalInOut(button_pin)
        tmp_pin.pull = Pull.UP
        self.button_debounce = Debouncer(tmp_pin,interval=0.01)
        self.forward = forward
        self.first_run = True
        self.cursor_col = cursor_col
        self.configs = configs
        self.active_config_no = 0
        self.active_config = configs[0]
    
    def set_range(self,min_val,max_val,turns,pulses_rev):
        self.min = min_val
        self.max = max_val
        self.turns = turns
        
    def set_pixel_col(self,pixel_number,new_col):
        if self.client.pixels[pixel_number] != new_col:
            self.client.pixels[pixel_number] = new_col
            self.client.controls_active = True
        
    def draw_cursor(self):
        for config in self.configs:
            base = config.pixel_start
            pixels = config.no_of_pixels
            pulse_limit = int(self.pulses_rev * config.turns)-1
            turn_amount = config.encoder_value / pulse_limit
            cursor = int(pixels*turn_amount)
            pos=0
            while pos < pixels:
                pix = base + pos
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
            
    def update_encoder(self):
        new_encoder_position = self.encoder.position
        encoder_change = self.last_encoder_position - new_encoder_position
        
        if encoder_change != 0 or self.first_run:
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
                self.draw_cursor()
                self.encoder_changed()
                
        self.last_encoder_position = new_encoder_position
        
    def update(self):
        self.button_debounce.update()
        if self.button_debounce.fell:
            self.button_down()
        if self.button_debounce.rose:
            self.button_up()
            
        self.update_encoder()

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
        
class ScreenCommand():

    def get_pixel_offset(self,x,y):
        return y*controller.panel_width + x

    def __init__(self, controller):
        self.controller = controller
 
    def process_command(self):
        input_buffer = self.controller.packet_input_buffer
        input_buffer_size = self.controller.packet_buffer_pos
        command_slice = slice(0,input_buffer_size)
        print("Processing command:", input_buffer[command_slice])
        default_length = len(self.defaults)
        if input_buffer_size < default_length:
            # the input buffer is shorter than the defaults
            # need to fill in some missing values
            for pos in range(input_buffer_size,self.controller.packet_buffer_pos):
                input_buffer[pos] = self.defaults[pos]
            # update the new length
            self.controller.packet_buffer_pos = default_length

# Fills a screen with the specified colour
class C_1_FillScreen(ScreenCommand):

    def __init__(self,controller):
        super(C_1_FillScreen,self).__init__(controller)
        # default colour values
        #               command  r  g  b 
        self.defaults = [1,       0, 0, 0]

    def process_command(self):
        super(C_1_FillScreen,self).process_command()
        input_buffer = self.controller.packet_input_buffer
        r = input_buffer[1]
        g = input_buffer[2]
        b = input_buffer[3]
        print("1 Setting panel colour r:",r," g:",g," b;",b)
        target = (r,g,b)

        for pixel in self.controller.pixel_managers:
            pixel.set_col(target)

# Fills a screen with the specified colour
class C_2_FadeScreen(ScreenCommand):

    def __init__(self,controller):
        super(C_2_FadeScreen,self).__init__(controller)
        # default colour values
        #               command   r  g  b  ticks to complete
        self.defaults = [1,       0, 0, 0, 5 ]
        self.current_step=0
        self.no_of_steps=0

    def process_command(self):
        super(C_2_FadeScreen,self).process_command()
        input_buffer = self.controller.packet_input_buffer
        r = input_buffer[1]
        g = input_buffer[2]
        b = input_buffer[3]
        target = (r,g,b)
        steps = input_buffer[4]
        for pixel in self.controller.pixel_managers:
            pixel.start_fade(target, steps)

# Draw a dot at a position on the screen 
class C_3_Drawdots(ScreenCommand):

    def __init__(self,controller):
        super(C_3_Drawdots,self).__init__(controller)
        # default colour values
        #                command  r  g  b  ticks to complete x1 y1 x2 y2 ... xn yn
        self.defaults = [1,       0, 0, 0, 5,                0,  0 ]
        self.current_step=0
        self.no_of_steps=0

    def process_command(self):
        super(C_3_Drawdots,self).process_command()
        input_buffer = self.controller.packet_input_buffer
        r = input_buffer[1]
        g = input_buffer[2]
        b = input_buffer[3]
        target = (r,g,b)
        steps = input_buffer[4]
        # now got a succession of x,y values that specify the dots to be drawn
        # work through these and add delta values for each of the pixels
        # need to clear the delta panel first of course.....
        # then the update will be just the same as for the fadescreen
        limit = self.controller.packet_buffer_pos
        pos = 5
        while pos < limit:
            x = input_buffer[pos]
            pos = pos + 1
            if pos == limit:
                break
            y = input_buffer[pos]
            pix_no = self.get_pixel_offset(x,y)
            self.controller.pixel_managers[pix_no].start_fade(target,steps)
            pos = pos + 1

# Draw a block at a position on the screen 
class C_4_DrawBlock(ScreenCommand):

    def __init__(self,controller):
        super(C_4_DrawBlock,self).__init__(controller)
        # default colour values
        #                command  r  g  b  ticks to complete x   y  w   h
        self.defaults = [1,       0, 0, 0, 5,                0,  0, 2,  2 ]
        self.current_step=0
        self.no_of_steps=0

    def process_command(self):
        super(C_4_DrawBlock,self).process_command()
        input_buffer = self.controller.packet_input_buffer
        r = input_buffer[1]
        g = input_buffer[2]
        b = input_buffer[3]
        steps = input_buffer[4]
        x = input_buffer[5]
        y = input_buffer[6]
        w = input_buffer[7]
        h = input_buffer[8]
        target = (r,g,b)
        for yp in range(0,h):
            fy = y + yp
            if fy < controller.panel_height:
                for xp in range (0,w):
                    fx = x + xp
                    if fx < controller.panel_width:
                        pix_no = self.get_pixel_offset(fx,fy)
                        self.controller.pixel_managers[pix_no].start_fade(target,steps) 

class DisplayController():
    def __init__(self):
        print("Rob Miles Chocolate Synthbox Interface 1.0")
        #                          TX         RX
        self.serial_port = busio.UART(board.GP8, board.GP9, baudrate=115200)
        base = 0
        c1 = [
            SerialControllerConfig(serial_port=self.serial_port, serial_channel=base+1,pixel_start=0,no_of_pixels=8),
            SerialControllerConfig(serial_port=self.serial_port, serial_channel=base+2, background_col = Col.YELLOW, pixel_start=8, no_of_pixels=8),
            SerialControllerConfig(serial_port=self.serial_port, serial_channel=base+3, background_col = Col.GREEN, pixel_start=16, no_of_pixels=8),
            SerialControllerConfig(serial_port=self.serial_port, serial_channel=base+4, background_col = Col.MAGENTA, pixel_start=24, no_of_pixels=8)
            ]
        
        c2 = [
            SerialControllerConfig(serial_port=self.serial_port,serial_channel=base+5,pixel_start=56),
            SerialControllerConfig(serial_port=self.serial_port,serial_channel=base+6, background_col = Col.YELLOW, pixel_start=48, no_of_pixels=8),
            SerialControllerConfig(serial_port=self.serial_port,serial_channel=base+7, background_col = Col.GREEN, pixel_start=40, no_of_pixels=8),
            SerialControllerConfig(serial_port=self.serial_port,serial_channel=base+8, background_col = Col.MAGENTA, pixel_start=32, no_of_pixels=8)
            ]
    
        self.controllers = [
            SerialController(client=self, name="c1", encoder_pin1=board.GP13, encoder_pin2=board.GP12, pulses_rev=20,
                           button_pin=board.GP16, forward=False, configs=c1),
            SerialController(client=self, name="c2", encoder_pin1=board.GP11, encoder_pin2=board.GP10, pulses_rev=20,
                           button_pin=board.GP17, forward=False,  configs=c2)
            ]

        self.setup_display_manager(board.GP18,8,8)

        self.setup_command_input()

    def button_down(self,controller):
        pass
        
    def button_up(self,controller):
        pass

    def encoder_changed(self, controller, change):
        pass

    def setup_display_manager(self, gpio, width,height):
        self.panel_width = width
        self.panel_height = height
        no_of_pixels = width*height
        self.pixels = neopixel.NeoPixel(gpio,no_of_pixels,auto_write=False)
        self.pixel_managers = []
        for i in range(0,no_of_pixels):
            self.pixel_managers.append(PixelManager(self.pixels,i))
        self.pixels.brightness = 0.3
        self.update_interval = 0.02
        self.controls_active = True
        self.next_update_time = time.monotonic() + self.update_interval
        self.control_display_end_time = time.monotonic() + 2

    AWAITING_START = 1
    READING_DATA = 2

    def process_incoming_packet(self):
        command_number = self.packet_input_buffer[0]
        command_processor = self.command_processors[command_number-1]
        command_processor.process_command()

    def setup_command_input(self,packet_buffer_length=256):
        # setup the command decoder
        self.command_processors = [
            C_1_FillScreen(self), 
            C_2_FadeScreen(self),
            C_3_Drawdots(self),
            C_4_DrawBlock(self)   
        ]

        # build the fixed length packet input buffer
        self.packet_input_buffer = []
        for i in range(0,packet_buffer_length):
            self.packet_input_buffer.append(0)
        self.packet_buffer_length = packet_buffer_length
        self.packet_buffer_pos=0
        self.command_changed_display = False
        self.packet_input_state = DisplayController.AWAITING_START
    
    def process_incoming_byte(self,b):
        separator = 255
        if self.packet_input_state == DisplayController.AWAITING_START:
            # If we get a separator - begin building the packet
            if b == separator:
                self.packet_buffer_pos=0
                self.packet_input_state = DisplayController.READING_DATA
        elif self.packet_input_state == DisplayController.READING_DATA:
            # If we get a separator we might have a command packet
            if b == separator:
                # Make sure we have a command to process
                if self.packet_buffer_pos > 0:
                    self.process_incoming_packet()
                    # reset the buffer
                    self.packet_buffer_pos = 0
                    # stay in the command reading state as the
                    # separator also starts the next packet
            else:
                # add the byte to the buffer
                if self.packet_buffer_pos == self.packet_buffer_length:
                    # If the packet is too long - discard it and wait for the next one
                    self.packet_input_state = DisplayController.AWAITING_START
                else:
                    # Store the byte and update the position
                    self.packet_input_buffer[self.packet_buffer_pos] = b
                    self.packet_buffer_pos = self.packet_buffer_pos + 1

    def process_incoming_bytes(self,bytes):
        for b in bytes:
            self.process_incoming_byte(b)

    def update(self):

        current_time = time.monotonic()

        self.controls_active == False

        for controller in self.controllers:
            controller.update()

        if self.controls_active:
            print("Controls active")
            self.controls_active = False
            self.control_display_end_time = current_time + 2

        incoming_bytes = self.serial_port.in_waiting
        if incoming_bytes != 0:
            serial_bytes = self.serial_port.read(incoming_bytes)
            self.process_incoming_bytes(serial_bytes)

        if current_time >= self.next_update_time:
            self.next_update_time = current_time + self.update_interval

            for pixel in self.pixel_managers:
                pixel.update()

            if current_time > self.control_display_end_time :
                for pixel in self.pixel_managers:
                    pixel.draw(self.pixels)

            self.pixels.show()

controller = DisplayController()

while True:
    controller.update()    
