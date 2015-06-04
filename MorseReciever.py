#!/usr/bin/env python
###Python program to take morse input on pin 7, decode to English and tweet the result...terribly coded by Matt and Emma

import pygame, time, RPi.GPIO as GPIO, thread, sys, pickle
from array import array
from pygame.locals import *
from morse_lookup import *
from twython import Twython
import Adafruit_CharLCD as LCD

#Enable the pins that let us read the morse keyer
pin = 4
#GPIO.setmode(GPIO.BCM) #If you don't import the Adafruit_CharLCD package, then this needs to be uncommented
GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # .PUD_UP for regualar morse key, .PUD_DOWN for peg key

# Raspberry Pi pin configuration:
lcd_rs        = 27  # Note this might need to be changed to 21 for older revision Pi's.
lcd_en        = 22
lcd_d4        = 25
lcd_d5        = 24
lcd_d6        = 23
lcd_d7        = 18
lcd_backlight = None

# Define LCD column and row size for 16x2 LCD.
lcd_columns = 16
lcd_rows    = 2

#Define a dot and dash in symbols
DOT = "."
DASH = "-"

#variable definitions
key_down_time = 0
key_down_length = 0
key_up_time = 0
message_buffer = []
buffer = []
output = [""]
your_name = "Steve"
last_message = ""

#Morse Code translation lengths
NEXT_LETTER_LENGTH = 1.0
NEXT_WORD_LENGTH = 3.0
DASH_LENGTH = 0.2

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

def title_splash():
    print ""
    print "_  _ ____ ____ ____ ____ ___  ____ ___      "
    print "|\/| |  | |__/ [__  |___ |__] |  |  |       "
    print "|  | |__| |  \ ___] |___ |__] |__|  |   v0.3"
    print "\n"
    lcd_print(2, "MorseBot v0.3")
    time.sleep(1)

def splash_screen(live_flag):
    try:
        if (live_flag == "True"): 
            print "Ready to Tweet!"
            lcd_print(1, "\nReady to Tweet!")
            time.sleep(1.5)
        else:
            print "Ready to Test..."
            lcd_print(2, "\nReady to Test!")
            time.sleep(1.5)
        find_name()
        print "\nPlease now transmit your message:"
        lcd_print(0, "")
        lcd_print(2, "Please transmit\nyour message:")
        time.sleep(2)
        lcd_print(0, "")
    except KeyboardInterrupt:
        print "Closed from Splash"

def find_name():
    global your_name 
    try:
        time.sleep(2)
        lcd_print(0, "")
        lcd_print(2, "Please Enter \nYour Name:")
        your_name = raw_input("Please enter your name: ")
        print "Thank you " + your_name + "."
        lcd_print(0, "")
        lcd_print(2, "Thank you\n" + your_name)
    except KeyboardInterrupt:
        print "\nOkay 'Steve'...please continue."
        lcd_print(0, "")
        lcd_print(2, "Okay 'Steve'\n Let's go...")

def post_tweet(message):
    print "Tweeting your message now:"
    lcd_print(0, "")
    lcd_print(2,"Tweeting your\nmessage now:")
    global api
    try:
        api.update_status(status=message)
        print "Tweeting Complete!\n"
        lcd_print(0, "")
        lcd_print(2,"Tweeting \nComplete!")
        time.sleep(1)
    except:
        print "Tweeting Failed...Sorry about that!!\n"
        lcd_print(0, "")
        lcd_print(2, "Tweeting Failed\nApologies")
        time.sleep(1)

def lcd_print(flag, message):
    #Flag definitions: 1=append; 2=clear;
    global lcd
    try:
        if flag is 0:
            del message_buffer[:]
            lcd.clear()
        if flag is 1:
            lcd.clear()
            if (len(message_buffer) == 17):
                message_buffer.append("\n")
        if flag is 2:
            del message_buffer[:]
        if flag is 3:
            if (len(message) > 16):
                message_list = [message[i:i+16] for i in range (0, 32, 16)]
                message = message_list[0] + "\n" + message_list[1]
        message_buffer.append(message)
        
    except:
        print("Message not correctly passed to LCD Thread")

def lcd_thread():
    global lcd
    global message_buffer
    global last_message
    local_message = ""
    first_flag = False
    while True:
        try:
            if first_flag == False:
                lcd.clear()
                first_flag = True
            time.sleep(.01)
            if len(message_buffer) > 0:
                local_message = "".join(message_buffer)
                if local_message != last_message:
                    lcd.message(local_message)
                    last_message = local_message
        except KeyboardInterrupt:
            print "\nClosing LCD Thread"
#            lcd_print(0, "")
#            lcd_print(2, "Closing Program")
#            time.sleep(1)
#            GPIO.cleanup(pin)
        except:
            print("Printing to the LCD failed")

def initiate_twitter_thread():
    #Twitter Calls to enable posting to the @getmorsebot account
    #pickle allows us to keep these keys secret in the "store.pckl" file!
    global api
    try:
        f = open('store.pckl')
        t_key = pickle.load(f)
        f.close()
        
        CONSUMER_KEY = t_key[0]
        CONSUMER_SECRET = t_key[1]
        ACCESS_KEY = t_key[2]
        ACCESS_SECRET = t_key[3]
        
        api = Twython(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_KEY,ACCESS_SECRET)
    except:
        print('Twitter setup failed') 

def decoder_thread():
    global key_up_time
    global buffer
    global output
    global live_flag
    new_word = False
    while True:
        try:
            time.sleep(.01)
            key_up_length = time.time() - key_up_time
            if len(buffer) > 0 and key_up_length >= NEXT_LETTER_LENGTH:
                new_word = True
                bit_string = "".join(buffer)
                output.append(try_decode(bit_string))
                lcd_print(1, output[len(output)-1])
                if (output[len(output) - 1] == 'EoT'):
                    output.remove('EoT')
                    print "\nThank you " + your_name + ". Your Message Follows:"
                    lcd_print(0, "")
                    lcd_print(2, "Thanks \n" + your_name)
                    time.sleep(3)
                    message = "".join(output)
                    print message[0:32]
                    lcd_print(0, "")
                    lcd_print(3, message)
                    time.sleep(5)
                    if (live_flag == "True"): 
                        post_tweet(your_name + ": " + message[0:32])
                    time.sleep(5)
                    first_flag = False
                    lcd_print(0, "")
                    title_splash()
                    splash_screen(live_flag)
                    del output[:]
                del buffer[:]
            elif new_word and key_up_length >= NEXT_WORD_LENGTH:
                new_word = False
                sys.stdout.write(" ")
                lcd_print(1, " ")
                output.append(" ")
                sys.stdout.flush()
        except KeyboardInterrupt:
            print "\nClosing Decoder Thread"
#            lcd_print(0, "")
#            lcd_print(2, "Closing Program")
#            time.sleep(1)
#            GPIO.cleanup(pin)

pygame.mixer.pre_init(44100, -16, 1, 1024)
pygame.init()
    
lcd = LCD.Adafruit_CharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows, lcd_backlight)

thread.start_new_thread(lcd_thread, ())

api = None
tone_obj = ToneSound(frequency = 800, volume = .5)

#Test the command line arguments to set if we're in practise or live mode
if (len(sys.argv) >= 2):
    live_flag = sys.argv[1]
else:
    live_flag = False

#if the flagg to tweet is true, then we open a thread to handle the api 
if (live_flag == "True"):
    thread.start_new_thread(initiate_twitter_thread, ())

#opening the translator thread and printing the Splash screen out to show that the program is ready
title_splash()

thread.start_new_thread(decoder_thread, ())
splash_screen(live_flag)

#state_main = True

#Main program thread loops through translating the keyer's presses into either dit or dah
while True:
    try:
        wait_for_keydown(pin)
        key_down_time = time.time() #record the time when the key went down
        tone_obj.play(-1) #the -1 means to loop the sound
        wait_for_keyup(pin)
        key_up_time = time.time() #record the time when the key was released
        key_down_length = time.time() - key_down_time #get the length of time it was held down for
        tone_obj.stop()
        buffer.append(DASH if key_down_length > DASH_LENGTH else DOT)
    except KeyboardInterrupt:
        print "\nClosing Program from Main"
        lcd_print(0, "")
        lcd_print(2, "Closing Program")
        time.sleep(1)
        GPIO.cleanup(pin)
        break