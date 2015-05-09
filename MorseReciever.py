#!/usr/bin/env python
import pygame, time, RPi.GPIO as GPIO, thread, sys, pickle
from array import array
from pygame.locals import *
from morse_lookup import *
from twython import Twython

#Morse Code translation lengths
NEXT_LETTER_LENGTH = 1.5
NEXT_WORD_LENGTH = 4.5
DASH_LENGTH = 0.15

pygame.mixer.pre_init(44100, -16, 1, 1024)
pygame.init()

api = None

class ToneSound(pygame.mixer.Sound):
    def __init__(self, frequency, volume):
        self.frequency = frequency
        pygame.mixer.Sound.__init__(self, self.build_samples())
        self.set_volume(volume)

    def build_samples(self):
        period = int(round(pygame.mixer.get_init()[0] / self.frequency))
        samples = array("h", [0] * period)
        amplitude = 2 ** (abs(pygame.mixer.get_init()[1]) - 1) - 1
        for time in xrange(period):
            if time < period / 2:
                samples[time] = amplitude
            else:
                samples[time] = -amplitude
        return samples

def wait_for_keydown(pin):
    while GPIO.input(pin):
        time.sleep(0.01)

def wait_for_keyup(pin):
    while not GPIO.input(pin):
        time.sleep(0.01)

def initiate_twitter_thread():
    #Twitter Calls to enable posting to the @getmorsebot account
    #pickle allows us to keep these keys secret!

    f = open('store.pckl')
    t_key = pickle.load(f)
    f.close()

    CONSUMER_KEY = t_key[0]
    CONSUMER_SECRET = t_key[1]
    ACCESS_KEY = t_key[2]
    ACCESS_SECRET = t_key[3]

    global api
    api = Twython(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_KEY,ACCESS_SECRET) 

def post_tweet(message):
    print "Tweeting your message now:"
    global api
    api.update_status(status=message)
    print "Tweeting Complete!"

def title_splash():
    print "\n"
    print "_  _ ____ ____ ____ ____ ___  ____ ___      "
    print "|\/| |  | |__/ [__  |___ |__] |  |  |       "
    print "|  | |__| |  \ ___] |___ |__] |__|  |   v0.1"
    print "\n"

def splash_screen(live_flag):
    if (live_flag == "True"): 
        print "Ready to Tweet!"
    else:
    	print "Ready to Test..."
    find_name()
    print "Please now transmit your message:"

def find_name():
    global your_name 
    your_name = raw_input("Please enter your name: ")
    print "Thank you " + your_name

def decoder_thread():
    global key_up_time
    global buffer
    global output
    new_word = False
    while True:
        time.sleep(.01)
        key_up_length = time.time() - key_up_time
        if len(buffer) > 0 and key_up_length >= NEXT_LETTER_LENGTH:
            new_word = True
            bit_string = "".join(buffer)
            output.append(try_decode(bit_string))
            if (output[len(output) - 1] == 'EoT'):
                output.remove('EoT')
                print "\nThank you " + your_name + ". Your Message Follows:"
                message = "".join(output)
                print message
                if (live_flag == "True"): 
                    post_tweet(message)
                    find_name()
                del output[:]
            del buffer[:]
        elif new_word and key_up_length >= NEXT_WORD_LENGTH:
            new_word = False
            sys.stdout.write(" ")
            output.append(" ")
            sys.stdout.flush()

tone_obj = ToneSound(frequency = 800, volume = .5)

#Test the command line arguements to set if we're in practise or live mode
if (len(sys.argv) >= 2):
    live_flag = sys.argv[1]
else:
    live_flag = False

if (live_flag == "True"):
    thread.start_new_thread(initiate_twitter_thread, ())

#Enable the pins that let us read the morse keyer
pin = 7
GPIO.setmode(GPIO.BOARD)
GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#Define a dot and dash in symbols
DOT = "."
DASH = "-"

#variable definitions
key_down_time = 0
key_down_length = 0
key_up_time = 0
buffer = []
output = [""]
your_name = "Steve"

#opening the translator thread and printing the Splash screen out to show that the program is ready
title_splash()
thread.start_new_thread(decoder_thread, ())
splash_screen(live_flag)

#Main program thread loops through translating the keyer's presses into either dit or dah
while True:
    wait_for_keydown(pin)
    key_down_time = time.time() #record the time when the key went down
    tone_obj.play(-1) #the -1 means to loop the sound
    wait_for_keyup(pin)
    key_up_time = time.time() #record the time when the key was released
    key_down_length = time.time() - key_down_time #get the length of time it was held down for
    tone_obj.stop()
    buffer.append(DASH if key_down_length > DASH_LENGTH else DOT)

#    This code prints the dash or dot to the command line for debug
#    if key_down_length > 0.15:
#        print DASH
#    else:
#        print DOT