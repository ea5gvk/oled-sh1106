from luma.core.interface.serial import i2c, spi, pcf8574
from luma.core.interface.parallel import bitbang_6800
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1309, ssd1325, ssd1331, sh1106, sh1107, ws0010
import time
from datetime import datetime
import math
import os

import subprocess

from board import SCL, SDA
import busio

from PIL import Image, ImageDraw, ImageFont

# rev.1 users set port=0
# substitute spi(device=0, port=0) below if using that interface
# substitute bitbang_6800(RS=7, E=8, PINS=[25,24,23,27]) below if using that interface
serial = i2c(port=1, address=0x3C)

# substitute ssd1331(...) or sh1106(...) below if using that device
device = sh1106(serial)
device.contrast(255)
screen_saver=300

width = device.width
height = device.height
image = Image.new("1", (width, height))
parrot = 0
text_parrot = ""
last_callsign = ""

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

font_path = str('/opt/oled/fonts/Roboto-Light.ttf')
font12 = ImageFont.truetype(font_path, 11)
font14 = ImageFont.truetype(font_path, 14)
font20 = ImageFont.truetype(font_path, 20)
font = ImageFont.truetype(font_path, 18)

def get_svxlog():
    f = os.popen('egrep -a -h "Talker start on|Talker stop on" /var/log/svxlink | tail -1')
    logsvx = str(f.read()).split(" ")
    if len(logsvx)>=2 and logsvx[4]=="start":
       CALL=logsvx[8].rstrip("\r\n")
       TalkG="TG "+logsvx[7].lstrip("#").rstrip(":")
    else:
       CALL=""
       TalkG=""
    return CALL,TalkG

def get_ip():
    cmd = "hostname -I | awk '{print $1}'"
    IP = subprocess.check_output(cmd, shell = True ).decode("utf-8")
    return "IP:  " + str(IP).rstrip("\r\n")+" "

def get_temp():
    # get cpu temperature
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as temp:
            tmpCel = int(temp.read()[:2])
    except:
        tmpCel = 0
    finally:
        return "T "+str(tmpCel)+" C"
#        return "T "+str(tmpCel)+"°C"

def get_cpuL():
    cmd = "top -bn1 | grep load | awk '{printf \"CPU : L %.2f,\", $(NF-2)}'"
    CPUL = subprocess.check_output(cmd, shell = True ).decode("utf-8")
    return CPUL

def get_svxlog_parrot():
    p = os.popen('egrep -a -h "module Parrot" /var/log/svxlink | tail -1')
    logsvx_parrot = str(p.read()).split(" ")
    if len(logsvx_parrot)>=2 and logsvx_parrot[3]=="Activating":
        text_parrot = "PARROT"
    else:
        text_parrot=""
    return text_parrot

def get_svxlog_metarinfo():
    m = os.popen('egrep -a -h "module MetarInfo" /var/log/svxlink | tail -1')
    logsvx_metarinfo = str(m.read()).split(" ")
    if len(logsvx_metarinfo)>=2 and logsvx_metarinfo[3]=="Activating":
        text_metarinfo = "METARINFO"
    else:
        text_metarinfo=""
    return text_metarinfo

def get_svxlog_echolink():
    e = os.popen('egrep -a -h "ctivating module EchoLink" /var/log/svxlink | tail -1')
    logsvx_echolink = str(e.read()).split(" ")
    if len(logsvx_echolink)>=2 and logsvx_echolink[3]=="Activating":
        text_echolink = "ECHOLINK"
    else:
        text_echolink=""
    return text_echolink

def get_svxlog_echolink_connection():
    c = os.popen('egrep -a -h "EchoLink QSO state changed" /var/log/svxlink | tail -1')
    logsvx_echolink_connection = str(c.read()).split(" ")
    if len(logsvx_echolink_connection)>=2 and logsvx_echolink_connection[8].rstrip("\r\n")=="CONNECTED":
       CONF=logsvx_echolink_connection[2].lstrip("*").rstrip(":").rstrip("*")
    else:
       CONF=""
    return CONF

def get_svxlog_echolink_callsign():
    s = os.popen('egrep -a -h ">" /var/log/svxlink | tail -1')
    logsvx_echolink_callsign = str(s.read()).split(" ")
    if len(logsvx_echolink_callsign)>=2:
       #CALLSIGN=logsvx_echolink_callsign[2].lstrip("-").lstrip(">")
       CALL=logsvx_echolink_callsign[2].lstrip(">")
       if (CALL.find('*') >= 0):
           NEWCALL = logsvx_echolink_callsign[3]
           CALLSIGN = NEWCALL.lstrip("(")
       else:
           CALLSIGN = CALL
    else:
       CALLSIGN=""
    return CALLSIGN

def get_svxlog_echolink_notalk():
    n = os.popen('egrep -a -h "' + last_callsign  + '" /var/log/svxlink | tail -1')
    logsvx_echolink_notalk = str(n.read()).split(" ")
    if len(logsvx_echolink_notalk)>=2:
       CALL=logsvx_echolink_notalk[2]
       if (CALL == last_callsign):
           retorno = "NOTALK"
       else:
           retorno = last_callsign
       return retorno
    else:
       return last_callsign 
    
    
text = (
    "TETRA-EA.DUCKDNS.ORG"
)
#maxwidth, unused = draw.textsize(text, font=font)
new_box = draw.textbbox((0,0), text, font)
maxwidth = new_box[2] - new_box[0]
unused = new_box[3] - new_box[1]

# Set animation and sine wave parameters.
amplitude = height / 4
offset = height / 2 - 2
velocity = -2
startpos = width
pos = startpos

# width in pixel screen
W=128

time_show="0"
count=0


while True:
    count =count+1
    # Draw a black filled box to clear the image.
    #draw.rectangle((0,0,width,height), outline=0, fill=0)
    check_svx_parrot = get_svxlog_parrot()
    check_svx_metarinfo = get_svxlog_metarinfo()
    check_svx_echolink = get_svxlog_echolink()
    check_svx_echolink_connection = get_svxlog_echolink_connection()
    check_svx_echolink_callsign = get_svxlog_echolink_callsign()
    check_svx_echolink_notalk = get_svxlog_echolink_notalk()
    print(last_callsign)
    print(check_svx_echolink_notalk)
    # get_svxlog_parrot_off()
    check_svx=get_svxlog()
    with canvas(device) as draw:
        if check_svx_parrot == "PARROT":
          time_show_parrot="0"
          count=0
          msg = str(check_svx_parrot)
          new_box = draw.textbbox((0,0), msg, font20)
          w = new_box[2] - new_box[0]
          draw.text(((W-w)/2, top+32),    msg,  font=font20, fill=255)
        else:
          time_show_parrot="1"  
        if check_svx_metarinfo == "METARINFO":
          time_show_metarinfo="0"
          count=0
          msg = str(check_svx_metarinfo)
          new_box = draw.textbbox((0,0), msg, font20)
          w = new_box[2] - new_box[0]
          draw.text(((W-w)/2, top+32),    msg,  font=font20, fill=255)
        else:
          time_show_metarinfo="1"  
        if check_svx_echolink == "ECHOLINK":
          time_show_echolink="0"
          count=0
          msg = str(check_svx_echolink)
          new_box = draw.textbbox((0,0), msg, font14)
          w = new_box[2] - new_box[0]
          draw.text(((W-w)/2, top+27),    msg,  font=font14, fill=255)
          msg = str(check_svx_echolink_connection)
          #w,h = draw.textsize(msg,font=font14)
          new_box = draw.textbbox((0,0), msg, font14)
          w = new_box[2] - new_box[0]
          draw.text(((W-w)/2, top+40),    msg,  font=font14, fill=255)
          if check_svx_echolink_notalk != "NOTALK":
              msg = str(check_svx_echolink_callsign)
              new_box = draw.textbbox((0,0), msg, font14)
              w = new_box[2] - new_box[0]
              draw.text(((W-w)/2, top+53),    msg,  font=font14, fill=255)
              last_callsign = msg
        else:
          time_show_echolink="1"
        if check_svx_echolink_notalk == "NOTALK":
          msg = "       "
          new_box = draw.textbbox((0,0), msg, font14)
          w = new_box[2] - new_box[0]
          draw.text(((W-w)/2, top+53),    msg,  font=font14, fill=255)
        if check_svx[0]!="" and check_svx_parrot!="PARROT" and check_svx_metarinfo!="METARINFO" and check_svx_echolink!="ECHOLINK":
          time_show="0"
          count=0
          msg = str(check_svx[1])
          #w,h = draw.textsize(msg,font=font14)
          new_box = draw.textbbox((0,0), msg, font14)
          w = new_box[2] - new_box[0]
          draw.text(((W-w)/2, top+32),    msg,  font=font14, fill=255)
          msg = str(check_svx[0])
          #w,h = draw.textsize(msg,font=font14)
          new_box = draw.textbbox((0,0), msg, font14)
          w = new_box[2] - new_box[0]
          draw.text(((W-w)/2, top+50),    msg,  font=font14, fill=255)
        elif check_svx[0]=="" and count<screen_saver and time_show_parrot=="1" and time_show_metarinfo=="1" and time_show_echolink=="1":
          now = datetime.now()
          current_time = now.strftime("Time: "+"%H:%M")
          msg = str(current_time)
          #w,h = draw.textsize(msg,font=font20)
          new_box = draw.textbbox((0,0), msg, font20)
          w = new_box[2] - new_box[0]
          draw.text(((W-w)/2, top+38),    msg,  font=font20, fill=255)
          time_show="1"
        if count<screen_saver:
          Temp = get_temp()
          CPUL = get_cpuL()
          msg = str(CPUL) + " "+str(Temp)
          draw.text((x, top), msg, font=font14, fill=255)

          msg = get_ip()
          #w,h = draw.textsize(msg,font=font12)
          new_box = draw.textbbox((0,0), msg, font12)
          w = new_box[2] - new_box[0]
          draw.text(((W-w)/2, top+16),  msg, font=font12, fill=255)

        # Screen saver
        if time_show=="1" and check_svx[0]=="" and count>screen_saver and time_show_parrot=="1":
          draw.rectangle((0, 0, width, height), outline=0, fill=0)
          xx = pos
          for i, c in enumerate(text):
            # Stop drawing if off the right side of screen.
            if xx > width:
                break
            # Calculate width but skip drawing if off the left side of screen.
            if xx < -10:
                #char_width, char_height = draw.textsize(c, font=font)
                new_box = draw.textbbox((0,0), c, font)
                char_width = new_box[2] - new_box[0]
                char_height = new_box[3] - new_box[1]
                xx += char_width
                continue
            # Calculate offset from sine wave.
            y = offset + math.floor(amplitude * math.sin(xx / float(width) * 2.0 * math.pi))
            # Draw text.
            draw.text((xx, y), c, font=font, fill=255)
            # Increment x position based on chacacter width.
            #char_width, char_height = draw.textsize(c, font=font)
            new_box = draw.textbbox((0,0), c, font)
            char_width = new_box[2] - new_box[0]
            char_height = new_box[3] - new_box[1]
            xx += char_width

        # Display image.
        #device.image(image)
        #device.show()

        # Move position for next frame.
        pos += velocity
        # Start over if text has scrolled completely off left side of screen.
        if pos < -maxwidth:
           pos = startpos
        if time_show=="1" and count>screen_saver:
          time.sleep(0.05)
        else:
          time.sleep(0.25)



    

