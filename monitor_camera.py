#! /usr/bin/python
# Written by Dan Mandle http://dan.mandle.me September 2012
# Enhanced by Carlos Ferreira Oct 26 2018
# License: GPL 2.0 
import os
from gps import *
from time import *
import time
import threading
import requests
import json

import sys
from imutils.video import VideoStream
import argparse
import datetime
import imutils

import re            # for finding USB devices
import shlex
import subprocess

#Libraries
import RPi.GPIO as GPIO

#import OpenCV
import cv2
# import cv2.cv as cv
# from common import clock, draw_str
 
#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)
 
#set GPIO Pins
GPIO_TRIGGER = 24
GPIO_ECHO = 23
 
#set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)

gpsd = None #seting the global variable
cam_count = 0 # number of cameras in system, using Microsoft only for now
HighRes_Cam = 0 #default is 0 camera 
address = 'NOWHERE' # address is global
Movement = False  #Default nobody home
Sonar_Movement = False # No Movement
vs = [] # init VS array

def Ping():
  GPIO.output(GPIO_TRIGGER, True)

  # set Trigger after 0.01ms to LOW
  time.sleep(0.00001)
  GPIO.output(GPIO_TRIGGER, False)

  StartTime = time.time()
  StopTime = time.time()

  # save StartTime
  while GPIO.input(GPIO_ECHO) == 0:
      StartTime = time.time()

  # save time of arrival
  while GPIO.input(GPIO_ECHO) == 1:
      StopTime = time.time()

  # time difference between start and arrival
  TimeElapsed = StopTime - StartTime
  # multiply with the sonic speed (34300 cm/s)
  # and divide by 2, because there and back
  dist = round((TimeElapsed * 34030) / 2)
  return dist

class GpsPoller(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    global gpsd #bring it in scope
    gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
    self.current_value = None
    self.running = True #setting the thread running to true

  def run(self):
    global gpsd
    while gpsp.running:
      gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
    print "Exiting GPS Thread...\n"
    
class SonarDistance(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    global distance #bring it in scope
    distance = 0
    self.current_value = None
    self.running = True #setting the thread running to true

  def run(self):
    global distance
    while sonar1.running:
      distance0 = Ping()
      time.sleep(2)
      distance1 = Ping()
      if distance1 > (distance0 + 10) or distance1 < (distance0 - 10):
        print 'SONAR detected Movement at distance ='+str(distance1)+' cm'
        Sonar_Movement = True
        distance = distance1
        time.sleep(5)
      else:
        Sonar_Movement = False
    print "Exiting Sonar Thread...\n"
    GPIO.cleanup()
    
class CamMovement(threading.Thread):
  def __init__(self):
    global cam_count
    global HighRes_Cam
    global vs
    threading.Thread.__init__(self)
    device_re = re.compile("\t/dev/video(?P<HDCam>\d+)$", re.I)
    args = shlex.split("v4l2-ctl --list-devices")
#    device_re = re.compile("Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id1>\w+)+:+(?P<id2>\w+)\s(?P<tag>.+)$", re.I)
    df = subprocess.check_output(args)
    lines = iter(df.split('\n'))
    for i in lines:
        if i:
            info = re.search("LifeCam\sStudio", i)
            if info:
                info = device_re.match(lines.next())
                if info:
                    dinfo = info.groupdict()
                    cam_count = cam_count + 1
                    HighRes_Cam = int(dinfo['HDCam'])
            else:
                info = re.search("\t/dev/video\d+$", i)
                if info:
                    cam_count = cam_count + 1
 
    i = 0
    
    print 'HighRes_Cam is '+str(HighRes_Cam)+'\n'
    
    while i < cam_count:
        try:
          vs.append(cv2.VideoCapture(i))
          if not vs[i].isOpened():
            print('No Webcam #'+str(i)+' \n')
            vs[i].release()
            vs.pop(i)
            i = i -1
            break
#          print 'Webcam: '+str(i)+' WIDTH: '+str(vs[i].get(3))+' HEIGHT: '+str(vs[i].get(4))+' FPS: '+str(vs[i].get(5))+' Format: '+str(vs[i].get(8))+' Mode: '+str(vs[i].get(9))+' Bright: '+str(vs[i].get(10))+' Contr: '+str(vs[i].get(11))+' Sat: '+str(vs[i].get(12))
          i = i+1
        except Exception as ex:
          template = "An exception of type {0} occurred. Arguments:\n{1!r}"
          message = template.format(type(ex).__name__, ex.args)
          print message
          print('ERROR CAUGHT: Webcam #'+str(i)+' \n')
          vs.pop(i)
          i = i -1
          break
    self.current_value = None
    self.running = True
    
    
  def run(self):
    global address
    global HighRes_Cam
    global Movement
    global vs
    firstFrame = None
    hits = 0                                 # counter for us to cycle over files
    
    #DEBUG
    # print 'DEBUG: Entering main camera monitor loop'
    #DEBUG
    CHNG_THRESH = 65   # Change Threshold used to be 25    
    
    while Move1.running:

      # grab the current frame and initialize the occupied/unoccupied
      retval, frame = vs[HighRes_Cam].read()
      text = "Unoccupied"
      
      #DEBUG
      # cv2.imwrite('FRAME.png', frame)
      #DEBUG
      
    	# if the frame could not be grabbed, then we have reached the end
    	# of the video
     
      if frame is None:
        break
    
    	# resize the frame, convert it to grayscale, and blur it
      
      frame = imutils.resize(frame, width=500)
      gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      gray = cv2.GaussianBlur(gray, (21, 21), 0)
    
      # if the first frame is None, initialize it
      if firstFrame is None:
        firstFrame = gray
        continue
    
      # compute the absolute difference between the current frame and
      # first frame
      frameDelta = cv2.absdiff(firstFrame, gray)
      thresh = cv2.threshold(frameDelta, CHNG_THRESH, 255, cv2.THRESH_BINARY)[1]
    
    	# dilate the thresholded image to fill in holes, then find contours
    	# on thresholded image
      thresh = cv2.dilate(thresh, None, iterations=2)
      cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
      cnts = cnts[0] if imutils.is_cv2() else cnts[1]
      
      # loop over the contours
      Caption = "Empty"
      for c in cnts:
    
        # compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = "Occupied"
        Caption = text+' !'
    
    	# draw the text and timestamp on the frame
      cv2.putText(frame, "Room Status: {}".format(Caption), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
      cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
      
    	# show the frame
      if text == "Occupied":
        print 'Movement detected '+datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p")
        print 'Location: '+address
        cv2.imwrite(str(hits)+'_Security'+'.png', frame)
        for x in range(cam_count):
          if x != HighRes_Cam:
            retval, frame = vs[x].read()
            Caption = str(x)
            cv2.putText(frame, "Camera: {}".format(Caption), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
            cv2.imwrite(str(hits)+'_Cam'+str(x)+'_'+'.png', frame)
        hits = hits + 1
        Movement = True
        sleep(4)            # give it 4 secs before you grab more frames
      else:
        Movement = False

      
      #DEBUG
      # print 'DEBUG: looping HITS='+str(hits)
      #DEBUG      
      
      if hits > 19:        # recycle videos so as not to eat space
        hits = 0
             
    print "Exiting Camera Thread...\n"
    i = 0
    while i < (cam_count-1):
        vs[i].release()
        vs.pop(i)
        i = i + 1
    

def get_image(ramp_frames):
    # read is the easiest way to get a full image out of a VideoCapture object.
    # Ramp the camera - these frames will be discarded and are only used to allow v4l2
    # to adjust light levels, if necessary
    for i in xrange(ramp_frames):
       temp = camera.read()
    retval, im = camera.read()
    return im
 
def detect(img, cascade):
    rects = cascade.detectMultiScale(img, scaleFactor=1.3, minNeighbors=4, minSize=(30, 30), flags = cv2.CASCADE_SCALE_IMAGE)
    if len(rects) == 0:
        return []
    rects[:,2:] += rects[:,:2]
    return rects

def draw_rects(img, rects, color):
    for x1, y1, x2, y2 in rects:
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)


if __name__ == '__main__':

  sys.stdout = open('monitor.log', 'w')
  print 'Camera and Sonar Monitoring Log for '+datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p")+'\n\n'
  
  gpsp = GpsPoller() # create the thread
  sonar1 = SonarDistance() # create sonar thread
  Move1 = CamMovement() # Open Cam and start checking for motion

  try:
    gpsp.start() # start it up
    sonar1.start() # start sonar
    while gpsd.fix.latitude == 0:
       time.sleep(3)
    
    ltlg = str(gpsd.fix.latitude)+','+str(gpsd.fix.longitude)
    payload = {'latlng': ltlg, 'key': 'AIzaSyCFAu81ebNZ36Bi557-SFKg19wMQ848EcU'}
   
    print "Latitude and Longitude: " + ltlg
    
    sys.stdout.flush()

    try:
      r = requests.get('https://maps.googleapis.com/maps/api/geocode/json', params=payload)
    except (Exception):
      print 'BAD HTTPS request'
      r = requests.get('http://www.google.com')
      r.ok = False

# For successful API call, response code will be 200 (OK)
    if(r.ok):
        # Loading the response data into a dict variable
        # json.loads takes in only binary or string variables so using content to fetch binary content
        # Loads (Load String) takes a Json file and converts into python data structure (dict or list, depending on JSON)
        jData = json.loads(r.content)

        # print("The response contains {0} properties".format(len(jData)))
        # print("\n")
        address = jData['results'][0]['formatted_address']
        print 'Monitoring at address: '+address+'\n' 
    else:
        # If response code is not ok (200), print the resulting http error code with description
        r.raise_for_status()
        print "Address API Error\n"

    Move1.start() # Start checking for movement
        
    while True:
      if Movement:
        print 'Camera detected movement might be at '+str(distance)+' cm'
      if Sonar_Movement:
        print 'Sonar detected movement at '+str(distance)+' cm'
      time.sleep(3) #set to whatever

  except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    print "\nKilling Thread..."
    Move1.running = False
    gpsp.running = False
    sonar1.running = False
    Move1.join() # wait for the thread to finish what it's doing
  print "Done.\nExiting."

 
