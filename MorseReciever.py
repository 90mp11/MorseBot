#!/usr/bin/env python
import pygame, time, RPi.GPIO as GPIO, thread, sys, pickle
from array import array
from pygame.locals import *
from morse_lookup import *
from twython import Twython

pygame.mixer.pre_init(44100, -16, 1, 1024)
pygame.init()

#Twitter Calls to enable posting to the @getmorsebot account
#pickle allows us to keep these keys secret!
f = open('store.pckl')
t_key = pickle.load(f)
f.close()

CONSUMER_KEY = t_key[0]
CONSUMER_SECRET = t_key[1]
ACCESS_KEY = t_key[2]
ACCESS_SECRET = t_key[3]


NEXT_LETTER_LENGTH = 1.5
NEXT_WORD_LENGTH = 4.5

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

def post_tweet(message):
    print "Tweeting your message now:"
    api.update_status(status=message)
    print "Tweeting Complete!"

def find_name():
    your_name = raw_input("Please enter your name: ")
    print "Thank you " + your_name

def splash_screen(live_flag):
	if (live_flag == "True"): #This flag will eventually allow for twitter/practise functionality
		print "Ready to Tweet!"
	else:
		print "Ready to Test..."
	find_name()
	print "Please now transmit your message:"

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
                del output[:]
            del buffer[:]
        elif new_word and key_up_length >= NEXT_WORD_LENGTH:
            new_word = False
            sys.stdout.write(" ")
            output.append(" ")
            sys.stdout.flush()

tone_obj = ToneSound(frequency = 800, volume = .5)
api = Twython(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_KEY,ACCESS_SECRET) 

live_flag = sys.argv[1]
message = 'Ready to Tweet!'

pin = 7
GPIO.setmode(GPIO.BOARD)
GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

DOT = "."
DASH = "-"

key_down_time = 0
key_down_length = 0
key_up_time = 0
buffer = []
output = [""]

thread.start_new_thread(decoder_thread, ())
splash_screen(live_flag)

while True:
    wait_for_keydown(pin)
    key_down_time = time.time() #record the time when the key went down
    tone_obj.play(-1) #the -1 means to loop the sound
    wait_for_keyup(pin)
    key_up_time = time.time() #record the time when the key was released
    key_down_length = time.time() - key_down_time #get the length of time it was held down for
    tone_obj.stop()
    buffer.append(DASH if key_down_length > 0.15 else DOT)

#    if key_down_length > 0.15:
#        print DASH
#    else:
#        print DOT