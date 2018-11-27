#! /usr/bin/python
# Enhanced by Carlos Ferreira Oct 26 2018
# License: GPL 2.0 
# import the necessary packages
import os
from imutils.video import VideoStream
import argparse
import datetime
import imutils
import time
import cv2


# initialize the first frame in the video stream
firstFrame = None
# loop over the frames of the video
hits = 0

# Open the Webcam 0. Assuming we have at least one

i = 0
vs = cv2.VideoCapture(i)
vs2 = vs

CHNG_THRESH = 50   # Change Threshold used to be 25

while vs2.isOpened() == TRUE:
    i = ++i
    vs2 = cv2.VideoCapture(i)
    if vs2.isOpened() == False:
        print('No Webcam #'+str(i)+' \n')
        vs2.release()
        del(vs2)
        break


try:
    while True:
      # grab the current frame and initialize the occupied/unoccupied
      # text
      retval, frame = vs.read()
      text = "Unoccupied"
      
    	# if the frame could not be grabbed, then we have reached the end
    	# of the video
     
      if frame is None:
        break
    
    	# resize the frame, convert it to grayscale, and blur it
     
      # cv2.imwrite('monitor.png', frame)
      
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
      # cv2.imshow("Security Feed", frame)
      # cv2.imshow("Thresh", thresh)
      # cv2.imshow("Frame Delta", frameDelta)
      if text == "Occupied":
        cv2.imwrite('Security'+str(hits)+'.png', frame)
        hits = hits+1
      # cv2.imwrite('Thresh.png', thresh)
      # cv2.imwrite('Delta.png', frameDelta)

        
except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    print "\nKilling Thread..."
    vs.release()
    del(vs)
    print "Done.\nExiting."
# cleanup the camera and close any open windows

# cv2.destroyAllWindows()