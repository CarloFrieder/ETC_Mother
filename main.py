import os
import pygame
import time
import random
import glob
import mvp_system
import imp
import socket
import traceback
import sys
import liblo
from pygame.locals import *
import alsaaudio, audioop
 
#create mvp object
mvp = mvp_system.System()
mvp.clear_flags()

# OSC init
try:
    osc_server = liblo.Server(4000)
except liblo.ServerError, err:
    print str(err)
    sys.exit()

osc_msgs_recv = 0

def fallback(path, args):
    global osc_msgs_recv
    osc_msgs_recv += 1

def knobs_callback(path, args):
    global osc_msgs_recv
    osc_msgs_recv += 1
    global mvp
    k1, k2, k3, k4, k5, k6 = args
    #mvp.knob1l = float(k4) / 1023
    #mvp.knob2l = float(k1) / 1023
    #mvp.knob3l = float(k2) / 1023
    #mvp.knob4l = float(k5) / 1023
    #mvp.knob5l = float(k3) / 1023

def keys_callback(path, args) :
    global osc_msgs_recv
    osc_msgs_recv += 1
    global mvp
    k, v = args
    if (k == 2 and v > 0) : mvp.next_patch = True
    if (k == 1 and v > 0) : mvp.prev_patch = True
    if (k == 9 and v > 0) : mvp.clear_screen = True
    if (k == 7 and v > 0) : mvp.screengrab = True
    if (k == 4 and v > 0) : mvp.prev_preset()
    if (k == 6 and v > 0) : mvp.save_preset()
    if (k == 5 and v > 0) : mvp.next_preset()
    if (k == 3 and v > 0) : 
        if (mvp.osd) : mvp.osd = False
        else : mvp.osd = True
    if (k == 8 and v > 0) : 
        if (mvp.auto_clear) : mvp.auto_clear = False
        else : mvp.auto_clear = True

    print str(k) + " " + str(v)

def midi_note_on_callback(path, args):
    global osc_msgs_recv
    osc_msgs_recv += 1
    global mvp
    c, n, v = args
    mvp.note_on = True
    mvp.note_num = n
    mvp.note_velocity = v
    #print n

def midi_cc_callback(path, args):
    global osc_msgs_recv
    osc_msgs_recv += 1
    global mvp
    c, n, v = args

    if n == 21 :
        mvp.knob1l = float(v) / 127
    if n == 22 :
        mvp.knob2l = float(v) / 127
    if n == 23 :
        mvp.knob3l = float(v) / 127
    if n == 24 :
        mvp.knob4l = float(v) / 127
    if n == 25 :
        mvp.knob5l = float(v) / 127
#    print args


osc_server.add_method("/knobs", 'iiiiii', knobs_callback)
osc_server.add_method("/key", 'ii', keys_callback)
osc_server.add_method("/mnon", 'iii', midi_note_on_callback)
osc_server.add_method("/mcc", 'iii', midi_cc_callback)
osc_server.add_method(None, None, fallback)

#setup alsa for sound in
inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,alsaaudio.PCM_NONBLOCK)
inp.setchannels(1)
inp.setrate(8000)
inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
inp.setperiodsize(300)

pygame.init()

# set up the colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
OSDBG = (0,0,255)

# OSD stuff
font = pygame.font.SysFont(None, 32)
notemsg = font.render('...', True, WHITE, OSDBG)

# setup a UDP socket for recivinng data from other programs
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(0)

# TODO :  make helper module, include functions like these :
def get_immediate_subdirectories(dir):
    return [name for name in os.listdir(dir)
            if os.path.isdir(os.path.join(dir, name))]

# init fb and main surfaces
print "opening frame buffer"
hwscreen = pygame.display.set_mode((1280,720),  pygame.FULLSCREEN | pygame.DOUBLEBUF, 32  )
screen = pygame.Surface(hwscreen.get_size())
screen.fill(GREEN) 
hwscreen.blit(screen, (0,0))
pygame.display.flip()
hwscreen.blit(screen, (0,0))
pygame.display.flip()
time.sleep(3)

# TODO :  don't make a list of moduels, just make a list of their names, and select them from  sys.modules
print "loading patches..."
patch_names = []
patch_folders = get_immediate_subdirectories('/usbdrive/Patches')

for patch_folder in patch_folders :
    patch_name = str(patch_folder)
    patch_path = '/usbdrive/Patches/'+patch_name+'/main.py'
    print patch_path
    try :
        imp.load_source(patch_name, patch_path)
        patch_names.append(patch_name)
    except Exception, e:
        print traceback.format_exc()

# set initial patch
num = 0
mvp.patch = patch_names[num]
patch = sys.modules[patch_names[num]]

# run setup functions if patches have them
# TODO: setup needs to get passed screen for things like setting sizes
for patch_name in patch_names :
    try :
        patch = sys.modules[patch_name]
        patch.setup(screen, mvp)
    except AttributeError :
        print "no setup found"
        continue 


# recent grabs
print 'loading recent grabs...'
mvp.tengrabs = []
mvp.tengrabs_thumbs = []
mvp.grabcount = 0
mvp.grabindex = 0
for i in range(0,11):
    mvp.tengrabs_thumbs.append(pygame.Surface((128, 72)))
    mvp.tengrabs.append(pygame.Surface(hwscreen.get_size()))

for filepath in sorted(glob.glob('/usbdrive/Grabs/*.bmp')):
    filename = os.path.basename(filepath)
    print 'loading grab: ' + filename
    img = pygame.image.load(filepath)
    img = img.convert()
    thumb = pygame.transform.scale(img, (128, 72) )
    #TODO : ensure img is 1280 x 720
    mvp.tengrabs[mvp.grabcount]= img
    mvp.tengrabs_thumbs[mvp.grabcount] = thumb
    mvp.grabcount += 1
    if mvp.grabcount > 10: break



buf = ''
line = ''
error = ''

count = 0
fps = 0
start = time.time()
clocker = pygame.time.Clock()

last_time = time.time()
this_time = 0

while 1:
    
    #check for OSC
    while (osc_server.recv(None)):
        pass
    #osc_server.recv(0)

    # get knobs from hardware or preset
    mvp.update_knobs()

    # quit on esc
    for event in pygame.event.get():
        if event.type == QUIT:
            exit()
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                exit()

    # measure FPS
    count += 1
    if ((count % 10) == 0):
        now = time.time()
        fps = 1 / ((now - start) / 10)
        start = now

    # get audio
    l,data = inp.read()
    triggered = False
    while l:
        for i in range(0,100) :
            try :
                avg = audioop.getsample(data, 2, i * 3)
                avg += audioop.getsample(data, 2, (i * 3) + 1)
                avg += audioop.getsample(data, 2, (i * 3) + 2)
                avg = avg / 3
                if (avg > 1000) :
                    triggered = True
                mvp.audio_in[i] = avg
            except :
                pass
        l,data = inp.read()
    
    # parse lines from UDP instead, this is from web
    try :
        data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        buf = buf + data
        if '\n' in buf :
            lines = buf.split('\n')
            for l in lines :
                mvp.parse_serial(l)
            buf = lines[-1]
    except :
        pass


    if mvp.next_patch: 
        error = ''
        num += 1
        if num == len(patch_names) : 
            num = 0
        mvp.patch = patch_names[num]
        patch = sys.modules[patch_names[num]]
    if mvp.prev_patch: 
        error = ''
        num -= 1
        if num < 0 : 
            num = len(patch_names) - 1
        mvp.patch = patch_names[num]
        patch = sys.modules[patch_names[num]]

    if mvp.clear_screen:
        screen.fill(mvp.bg_color) 

    if mvp.auto_clear :
        screen.fill(mvp.bg_color) 

    mvp.bg_color =  mvp.color_picker_bg()
    
    # set patch
    if mvp.set_patch :
        error = ''
        print "setting: " + mvp.patch
        try :
            patch = sys.modules[mvp.patch]
        except KeyError:
            error = "Module " +mvp.patch+ " is not loaded, probably it has errors"

    # reload
    if mvp.reload_patch :
        error = ''
        # delete the old
        if mvp.patch in sys.modules:  
            del(sys.modules[mvp.patch]) 
        print "deleted module, reloading"
        patch_name = mvp.patch
        patch_path = '/usbdrive/Patches/'+patch_name+'/main.py'
        try :
            patch = imp.load_source(patch_name, patch_path)
            print "reloaded"
            
            # then call setup
            try :
                patch.setup(screen, mvp)
            except Exception, e:
                error = traceback.format_exc()
        except Exception, e:
            error = traceback.format_exc()
    
    try :
        patch.draw(screen, mvp)
    except Exception, e:
        error = traceback.format_exc()
 
    #save frame
    if mvp.screengrab:
        filenum = 0
        imagepath = "/usbdrive/Grabs/" + str(filenum) + ".bmp"
        imagepath_thumb = "/usbdrive/Grabs/" + str(filenum) + "_thumb.bmp"
        while os.path.isfile(imagepath):
            filenum += 1
            imagepath = "/usbdrive/Grabs/" + str(filenum) + ".bmp"
            imagepath_thumb = "/usbdrive/Grabs/" + str(filenum) + "_thumb.bmp"
        pygame.image.save(screen,imagepath)
        # add to the grabs array
        #grab = screen
        mvp.grabindex += 1
        mvp.grabindex %= 10
        pygame.transform.scale(screen, (128, 72), mvp.tengrabs_thumbs[mvp.grabindex] )
        pygame.image.save(mvp.tengrabs_thumbs[mvp.grabindex],imagepath_thumb)
        mvp.tengrabs[mvp.grabindex] = screen.copy()
        print imagepath
   
    #draw the main screen
    hwscreen.blit(screen, (0,0))
    
    # osd
    if mvp.osd :
        this_time = time.time()
        elapsed_time = this_time - last_time
        last_time = this_time
        osc_msgs_per_sec = osc_msgs_recv / elapsed_time
        #osd.fill(GREEN) 
        pygame.draw.rect(hwscreen, OSDBG, (0, hwscreen.get_height() - 40, hwscreen.get_width(), 40))
        font = pygame.font.SysFont(None, 32)
        text = font.render(str(patch.__name__) + ', frame: ' + str(count) + ', fps: ' + str(int(fps)) + ', Auto Clear: ' + str(mvp.auto_clear) + ', osc: ' + str(osc_msgs_recv) + ', osc / sec: ' + str(osc_msgs_per_sec), True, WHITE, OSDBG)
        text_rect = text.get_rect()
        text_rect.x = 50
        text_rect.centery = hwscreen.get_height() - 20
        hwscreen.blit(text, text_rect)

        for i in range(0,10) :
            hwscreen.blit(mvp.tengrabs_thumbs[i], (128 * i,0))

        # osd, errors
        i = 0
        for errorline in error.splitlines() :
            errormsg = font.render(errorline, True, WHITE, RED) 
            text_rect = notemsg.get_rect()
            text_rect.x = 50
            text_rect.y = 20 + (i * 32)
            hwscreen.blit(errormsg, text_rect)
            i += 1

    #clocker.tick(35)
    pygame.display.flip()

    if mvp.quit :
        sys.exit()
    
    # clear all the events
    mvp.clear_flags()
    osc_msgs_recv = 0

time.sleep(1)


print "Quit"
