# chocolate-synthbox
Raspberry Pi and PICO powered musical instrument running Pure Data


![Chocolate Synthbox, midi CheeseBox and crackers controller](images/synthbox%20cheesebox%20and%20crackers.jpg)
# Video
[![YouTube Screenshot](images/Video%20Title.jpg)](https://youtu.be/IFDrWa9PeCk)

To find out more about the device click on the image above to see a short video.
# Parts list
* Raspberry Pi. The software works with any Pi from the Zero upwards, but for more interesting sounds a Pi 4 is best
* Pi soundcard and amplifier. I used the Waveshare WM8960 but you can also use the Adafruit I2S 3W stereo speaker bonnet
* Pixel panel. The prototype uses an Adafruit NeoPixel NeoMatrix 8x8 - 64 RGB LED Pixel Matrix. This board is 71mm x 71mm. You can get WS2812 8x8 pixel matrices which are smaller (65mm square). There are printable case designs for each size. 
* Two rotary encoders (search for KY-040 encoder)
* A small speaker (You can get a very nice one from Pimoroni: https://shop.pimoroni.com/products/mini-speaker-4-3w)
* You can get the connectors you need to power the Pi and the PICO buy buying a USB-C Power Splitter for Raspberry Pi Touchscreen Display
* A Female 5.5mm x 2.1mm power socket 
* A power supply capable of supplying 5 volts at least 4 amps with a 5.5mm x 2.1mm plug.
* Connecting wire (search for "30 AWG wire wrap") which needs a wire wrap tool (search for "wire wrap tool").
* A box. There are a 3D printable designs available.
* Screws. You'll need some screws sized M2 4mm in length to fix things to the case (search for "laptop screws")
# Circuit Diagram
![device circuit diagram](images/Synthbox%20circuit.png)
# Set up the Pico
Copy the program and libraries onto the Pico device. The Pico program is in the file code.py in the root of this repository. This is so you can use the Pymakr plugin to download and run the program from this repository. You will need to copy the contents of the lib folder onto your Pico as this contains Circuit Python libraries. 
# Set up the Raspberry Pi
## Get the operating system
Install the latest version of the Raspberry Pi operating system. Don't install the headless version because you will  need to use the desktop to configure Pure Data.
## Install the sound hardware 
Plug your sound hat onto your Raspberry Pi and install the driver software for it. If you are using the WaveShare sound hat you can use the installer [here](https://www.waveshare.com/wiki/WM8960_Audio_HAT#Install_Driver).

## Enable serial port 2
Note that serial port 2 in this configuration only works on a Raspberry Pi 4. 
Enable the serial port 2. This is the port that links the Pi to the Pico. We are going to use the second serial port which is exposed as /dev/ttyAMA1. It uses the GPIO0 (TX) and GPIO1 (RX) pins on the Raspberry Pi. These are on pins 27 and 28 respectively on the GPIO connector. We enable this port by adding the following line at the end of the file /boot/config.txt:
```
sudo nano /boot/config.txt
```
![nano editing config.txt](images/adding%20serial%20port.png)

```
dtoverlay=uart2
```
Add the line as show above, write and save the file. If you want to use a different serial port you will have to modify the SerialComms.pd patch to change the name of the serial device it uses. 
## Install Pure Data and the Pure Data comport
Open up a terminal window and type:
```
sudo apt-get install puredata
sudo apt install pd-comport
```
This will install Pure Data and the comport object used by Pure Data patches to communicate over the serial port. 
## Copy the Pure Data patches to the Pi
You can use a usb drive or a remote desktop connection to copy these onto the your Pi. Copy the  Synthbox folder in the pd-code folder onto the desktop of your Pi. You must put the folder here, otherwise it won't be picked up automatically when the Pi starts. 
![Synthbox on the desktop](images/synthbox%20on%20the%20desktop.png)
## Make Pure Data start on bootup
We can make Pure Data to start each time the Raspberry Pi boots by adding a line to the /etc/xdg/lxsession/LXDE-pi/autostart file. Open the file as follows:
```
sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
```
![nano editing autostart](images/auto%20starting%20Pure%20Data.png)

Add the line:
```
sudo pd /home/pi/Desktop/Synthbox/ChocSynthboxMain.pd
```
Save the file and close it. Now each time your Pi starts it will run PureData.
## Connect Pure Data to the audio output
Next you need to tell Pure Data to use the audio output device we have installed.
Open up a desktop connection to the Pi, open Pure Data if it is not running and then select File>Preferences>Audio 
![Selecting Pure Data sound output](images/puredata%20sound%20output%20select.png)
Click the input and output devices buttons and select the seeed devices as shown above. 
Then click Save All Settings and OK to save the settings and close the dialog.
## Connect Pure Data to your MIDI devices
Make sure that you have plugged your MIDI devices in before you start Pure Data running. It seems to only check for devices on startup. Open File>Preferences>Midi and select the option to use multiple devices. 
![Selecting Pure Data sound output](images/puredata%20midi%20select.png)
Then select the MIDI input devices and click Save All Settings and then OK to close the dialog. 
## Run the patch
![Pure Data console](images/Synthbox%20console.png)
When the patch is running the above is displayed on the Pi screen. You can use the sliders to adjust the values that are also controlled by the Pico Crackers controller. 

This is a work in progress. But it is fun to play with. 

I hope you have fun with it.

Rob Miles