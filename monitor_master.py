#! /usr/bin/python
# Written by Dan Mandle http://dan.mandle.me September 2012
# Enhanced by Carlos Ferreira Dec 5, 2018
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
import multiprocessing as mp

#Libraries
import RPi.GPIO as GPIO

#import OpenCV
import cv2
# import cv2.cv as cv
# from common import clock, draw_str
import signal

#set GPIO Pins
GPIO_TRIGGER = 24
GPIO_ECHO = 23

Sonar_Run = True
GPS_Run = True
Cam_Run = True
All_Run = True

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

def sigterm_sonar(_signo, _stack_frame):
    global Sonar_Run
    Sonar_Run = False

def SonarDistance(qs):
    global Sonar_Run
    #GPIO Mode (BOARD / BCM)
    GPIO.setmode(GPIO.BCM)

    #set GPIO direction (IN / OUT)
    GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
    GPIO.setup(GPIO_ECHO, GPIO.IN)
    distance = 0
    signal.signal(signal.SIGTERM, sigterm_sonar)
    signal.signal(signal.SIGINT, sigterm_sonar)

    while Sonar_Run:
      distance0 = Ping()
      time.sleep(2)
      distance1 = Ping()
      if distance1 > (distance0 + 10) or distance1 < (distance0 - 10):
        qs.put(distance1)
        distance = distance1
        time.sleep(5)
    GPIO.cleanup()

def sigterm_gps(_signo, _stack_frame):
    # Raises SystemExit(0):
    global GPS_Run
    GPS_Run = False

def GpsPoller(qg):
    global GPS_Run
    gpsdt = gps(mode=WATCH_ENABLE) #starting the stream of info
    signal.signal(signal.SIGTERM, sigterm_gps)
    signal.signal(signal.SIGINT, sigterm_gps)
    while gpsdt.fix.latitude == 0:
        gpsdt.next()
        time.sleep(3)
    while GPS_Run:
      time.sleep(3)        # don't loop like crazy....
      if qg.empty():      # only get GPS coordinate if someone pulled the location out.....
        gpsdt.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
        qg.put([gpsdt.fix.latitude, gpsdt.fix.longitude])

def sigterm_cam(_signo, _stack_frame):
    # Raises SystemExit(0):
    global Cam_Run
    Cam_Run = False
   
def CamMovement(qc):
    global Cam_Run
    firstFrame = None
    hits = 0                                 # counter for us to cycle over files

    CHNG_THRESH = 65   # Change Threshold used to be 25    

    HR_Cam = qc.get()
    
    cc = qc.get()
    i = 0
   
    vs = [] # init VS array
  
    while i < cam_count:
      vs.append(cv2.VideoCapture(i))
      if not vs[i].isOpened():
        print('Could not open webcam #'+str(i)+' \n')
        vs[i].release()
        vs.pop(i)
        i = i-1
        break
      i = i+1
    
    signal.signal(signal.SIGTERM, sigterm_cam)
    signal.signal(signal.SIGINT, sigterm_cam)
    
    while Cam_Run:

      # grab the current frame and initialize the occupied/unoccupied
      retval, frame = vs[HR_Cam].read()
      text = "Unoccupied"
          
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
        if (w > 10) and (h > 10):                                        # trying to eliminate tiny changes
          cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
          text = "Occupied"
          Caption = text+' !'
    
    	# draw the text and timestamp on the frame
      cv2.putText(frame, "Room Status: {}".format(Caption), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
      cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
      
    	# show the frame
      if text == "Occupied":
        cv2.imwrite(str(hits)+'_Security'+'.png', frame)
        for x in range(cc):
          if x != HR_Cam:
            retval, frame = vs[x].read()
            Caption = str(x)
            cv2.putText(frame, "Camera: {}".format(Caption), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
            cv2.imwrite(str(hits)+'_Cam'+str(x)+'_'+'.png', frame)
        hits = hits + 1
        qc.put([True, datetime.datetime.now()])

        sleep(4)            # give it 4 secs before you grab more frames

      if hits > 19:        # recycle videos so as not to eat space
        hits = 0
    i = 0
    while i < (cam_count-1):
      vs[i].release()
      vs.pop(i)
      i = i + 1

def sigterm_main(_signo, _stack_frame):
    global All_Run
    All_Run = False
             
if __name__ == '__main__':


  signal.signal(signal.SIGTERM, sigterm_main)
  signal.signal(signal.SIGINT, sigterm_main)

  cam_count = 0 # number of cameras in system, using Microsoft only for now
  HighRes_Cam = 0 #default is 0 camera 

  sys.stdout = open('monitor.log', 'w')
  print 'Camera and Sonar Monitoring Log for '+datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p")+'\n\n'
  
  device_re = re.compile("\t/dev/video(?P<HDCam>\d+)$", re.I)
  args = shlex.split("v4l2-ctl --list-devices")
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

  qs = mp.Queue()
  qg = mp.Queue()
  qc = mp.Queue()
  
  qc.put(HighRes_Cam)
  qc.put(cam_count)

  ps = mp.Process(target=SonarDistance, args=(qs,))
  pg = mp.Process(target=GpsPoller, args=(qg,))
  pc = mp.Process(target=CamMovement, args=(qc,))

  pg.start()
  ps.start()
  pc.start()

  while qg.empty():
    time.sleep(2)
    if not qg.empty():
      break
  lat, lng = qg.get()    
  ltlg = str(lat)+','+str(lng)
  payload = {'latlng': ltlg, 'key': 'AIzaSyCFAu81ebNZ36Bi557-SFKg19wMQ848EcU'}

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

  while All_Run:
    if not qs.empty():
      dist = qs.get()
      print '****SONAR**** detected movement might be at '+str(dist)+' cm'
    if not qc.empty():
      mov, movdate = qc.get()
      print '####CAMERA#### detected movement on '+movdate.strftime("%A %d %B %Y %I:%M:%S%p")
      print 'Location: '+address
    time.sleep(3) #set to whatever

  print "\nKilling Children..."
  pc.terminate()
  print "Exiting Camera Process..."
  ps.terminate()
  print "Exiting Sonar Process..."
  pg.terminate()
  print "Exiting GPS Process..."

  print "Done.\nExiting."

 
