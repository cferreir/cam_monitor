#! /usr/bin/python
# Enhanced by Carlos Ferreira Oct 26 2018
# License: GPL 2.0 
# import the necessary packages
import os
import time
from time import *
import sys
from imutils.video import VideoStream
import argparse
import datetime
import imutils
import cv2



# initialize the first frame in the video stream
firstFrame = None
# loop over the frames of the video
hits = 0

# Open the Webcam 0. Assuming we have at least one

i = 0
vs = [cv2.VideoCapture(i)]

CHNG_THRESH = 50   # Change Threshold used to be 25

# import number of cameras
if os.environ.get('CAMERA_COUNT'):
    cam_count = int(os.environ['CAMERA_COUNT']) - 1
else:
    cam_count = 0

while i < cam_count:
    i = i+1
    try:
      vs.append(cv2.VideoCapture(i))
      if not vs[i].isOpened():
        print('No Webcam #'+str(i)+' \n')
        vs[i].release()
        vs.pop(i)
        i = i -1
        break
    except Exception as ex:
      template = "An exception of type {0} occurred. Arguments:\n{1!r}"
      message = template.format(type(ex).__name__, ex.args)
      print message
      print('ERROR CAUGHT: Webcam #'+str(i)+' \n')
      vs.pop(i)
      i = i -1
      break



try:
    while True:
      # grab the current frame and initialize the occupied/unoccupied
      # text
      retval, frame = vs[0].read()
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
      for c in cnts:
    
        # compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = "Occupied"
    
    	# draw the text and timestamp on the frame
      cv2.putText(frame, "Room Status: {}".format(text), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
      cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
      
    	# show the frame and record if the user presses a key

      if text == "Occupied":
        cv2.imwrite('Security'+str(hits)+'.png', frame)
        for x in range(cam_count):
          retval, frame = vs[x+1].read()
          cv2.imwrite('Cam'+str(x+1)+'_'+str(hits)+'.png', frame)
        hits = hits+1
        time.sleep(4)      # detected motion sleep 4 seconds to confirm

      if hits > 19:        # recycle videos so as not to eat space
        hits = 0
        
except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    print "\nKilling Thread..."
    i = 0
    while i <= cam_count:
        vs[i].release()
        del(vs[i])
        i = i + 1

    print "Done.\nExiting."
# cleanup the camera and close any open windows

# cv2.destroyAllWindows()