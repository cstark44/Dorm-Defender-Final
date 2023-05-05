# import required modules
from flask import Flask, render_template, Response, jsonify, request, redirect
import os
import cv2
import subprocess
from subprocess import Popen, PIPE, check_output
from multiprocessing import Process
from gpiozero import MotionSensor
import textAlerts
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
from datetime import datetime
import time
from pydub import AudioSegment
from pydub.playback import play
app = Flask(__name__) 
vc = cv2.VideoCapture(0) 

stream = []
settings = []

# Helper Functions 
def getLink():
   # When disconnected from ssh
   return str(subprocess.check_output("hostname -I",stdin=None,stderr=subprocess.STDOUT,shell=True)).split(" ", 3)[0][2:] + ":5000"
   # When connected to ssh
   # return str(subprocess.check_output("hostname -I",stdin=None,stderr=subprocess.STDOUT,shell=True)).split(" ", 3)[1] + ":5000"
  
def validPhoneNumber(phoneNumber):
   '''Determines whether the phone number is 10 digits and valid or not'''
   return len(phoneNumber) == 10

def sendAlert(alertType, alertSetting, phoneNumber):
   '''Helper function to send text alerts using the textAlerts python program'''
   # Get web address CS 120 starter code - written by Lisa Dion
   link = getLink()
   if (alertSetting == "both" or alertSetting == "motion") and alertType == "motion":
      if validPhoneNumber(phoneNumber):
         print("sent")
         textAlerts.sendMessage(phoneNumber, "Dorm Defender: There is motion at your door. Live video can be found here:")
         textAlerts.sendMessage(phoneNumber, link)
   elif (alertSetting == "both" or alertSetting == "ring") and alertType == "ring":
      if validPhoneNumber(phoneNumber):
         print("sent")
         textAlerts.sendMessage(phoneNumber, "Dorm Defender: Someone is at your door. Live video can be found here: ")
         textAlerts.sendMessage(phoneNumber, link)

def buttonPress():
   '''Checks for button presses and sends notifications when input is received'''
   while True: # Run forever
      if GPIO.input(10) == GPIO.HIGH:
         # Write so that the stream function stops streaming video so a picture can be taken
         f = open("video.txt", "w")
         f.write("false")
         f.close()

         # Simulate traffic so that a image will be generated 
         command = "curl http://" + getLink() + "/video_feed"
         subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
         
         print("Button was pushed!")
         currentDateAndTime = datetime.now()

         # Check settings to get phone number and time preference
         settings.clear()
         f = open("settings.txt", "r")
         for line in f:
            line = line.strip()
            settings.append(line)
         f.close()
         print(settings[0])
         hour = currentDateAndTime.hour;
         if hour > 12 and settings[1] == "standard":
            hour -= 12;
         
         # Double check minute and add on 0 before if it is less than 10
         if currentDateAndTime.minute < 10:
            minute = "0" + str(currentDateAndTime.minute)
         else:
            minute = str(currentDateAndTime.minute)

         # Move the image to the images folder
         command2 = "cp pic.jpg /home/cmstark/Desktop/CS121/dorm_defender/static/photos/" + "ring_" + str(currentDateAndTime.month) + "-" + str(currentDateAndTime.day) + "-" + str(currentDateAndTime.year) + "_" + str(currentDateAndTime.hour)+ ":" + minute + ".png"
         subprocess.check_output(command2,stdin=None,stderr=subprocess.STDOUT,shell=True)

         time.sleep(0.5)
         # Write that live video can be streamed again
         f = open("video.txt", "w")
         f.write("true")
         f.close()

         # Play sound
         soundName = "sounds/" + settings[3]
         sound = AudioSegment.from_wav(soundName)
         play(sound)

         # Rewrite page
         detectedAt = str(hour) + ":" + minute + " " + str(currentDateAndTime.month) + "/" + str(currentDateAndTime.day) + "/" + str(currentDateAndTime.year)
         message = "Doorbell Rang " + detectedAt + "\n"
         f = open("stream.txt", "a")
         f.write(message)
         f.close()

         # Send notification
         number = settings[0]
         print(number)
         alertSetting = settings[2]
         sendAlert("ring", alertSetting, number)
         
def movement():
   '''Checks for movement and sends notifications if there is new movement after 5 seconds of no movement'''
   # Set up motion sensor and initialize the last movement time
   lastMovement = time.time() - 11
   pirSensor = MotionSensor(4)
   while True:
      pirSensor.wait_for_motion()
      if (time.time() - lastMovement > 10):
         print("Motion Detected")
         currentDateAndTime = datetime.now()
            
         # Check settings to get phone number and time preference
         settings.clear()
         f = open("settings.txt", "r")
         for line in f:
            line = line.strip()
            settings.append(line)
         f.close()
         hour = currentDateAndTime.hour;
         if hour > 12 and settings[1] == "standard":
            hour -= 12;
             
         # Double check minute and add on 0 before if it is less than 10
         if currentDateAndTime.minute < 10:
            minute = "0" + str(currentDateAndTime.minute)
         else:
            minute = str(currentDateAndTime.minute)
            
         # Send alert
         alertSetting = settings[2]
         number = settings[0]
         sendAlert("motion", alertSetting, number)
         # Rewrite page
         detectedAt = str(hour) + ":" + minute + " " + str(currentDateAndTime.month) + "/" + str(currentDateAndTime.day) + "/" + str(currentDateAndTime.year)
         message = "Motion Detected " + detectedAt + "\n"
         f = open("stream.txt", "a")
         f.write(message)
         f.close()
      lastMovement = time.time() 

# Start background processes to constantly check if there is button presses or movements
buttonBackground = Process(target=buttonPress)
buttonBackground.start()
motionBackground = Process(target=movement)
motionBackground.start()

@app.route('/', methods =["GET", "POST"]) 
def index(): 
   '''Main page with video streaming'''
   # Get stream from file 
   stream.clear()
   f = open("stream.txt", "r")
   for line in f:
      stream.insert(0, line)
   f.close()

   # Render the template
   return render_template('index.html', stream=stream) 

def gen(): 
   '''Video streaming generator function. Gets the frame and saves it so it can be sent to the web server'''
   while True: 
      # Check to see if photo is being taken, if it is, dont stream the video
      f = open("video.txt", "r")
      streamAllowed = f.readline()
      f.close()
      if streamAllowed == "true":
         rval, frame = vc.read() 
         frame = cv2.rotate(frame, cv2.ROTATE_180)
         cv2.imwrite('pic.jpg', frame) 
         yield (b'--frame\r\n' 
               b'Content-Type: image/jpeg\r\n\r\n' + open('pic.jpg', 'rb').read() + b'\r\n') 

@app.route('/video_feed', methods =["GET", "POST"]) 
def video_feed(): 
   '''Video streaming route.'''
   return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame') 

@app.route('/settings', methods= ["GET", "POST"])
def open_settings():
   data = request.get_json()
   return render_template('settings.html', data = data)

@app.route('/photos')
def display_photos():
   photoNames = []
   photos = os.listdir('static/photos')
   photos = ['photos/' + file for file in photos]
   photos.sort()
   photos.reverse()
   return render_template('photos.html', photos = photos)

@app.route('/settings_submit', methods=['GET', 'POST'])
def submit_settings():
   # Get the data entered
   data = request.form

   # Write the data
   f = open("settings.txt", "w")
   f.write(data.get('phone_number') + "\n")
   f.write(data.get('time_preference') + "\n")
   f.write(data.get('alert_preference') + "\n")

   # Write the correct file name based on the entry
   if (data.get('door_bell') == "harp"):
      f.write("dream-harp-06.wav")
   elif (data.get('door_bell') == "traditional_2"):
      f.write("doorbell-2.wav")
   elif (data.get('door_bell') == "futuristic"):
      f.write("futuristic-doorbell.wav")
   else:
      f.write("doorbell-real.wav")
   f.close()

   # Redirect back to the home page
   return redirect('/')

if __name__ == '__main__': 
   app.run()#host='0.0.0.0', debug=True, threaded=True) 
