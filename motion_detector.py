import cv2 as open_cv
import numpy as np
import logging
import requests
from drawing_utils import draw_contours
from colors import COLOR_GREEN, COLOR_WHITE, COLOR_BLUE, COLOR_YELLOW,COLOR_PINK
from threading import Thread
import threading
import time
import base64
import json
import yaml
from openalpr_api import alpr
from datetime import datetime
from time import sleep
x=[]

class MotionDetector:
    LAPLACIAN = 1.4
    DETECT_DELAY = 1

    def __init__(self, video, coordinates, start_frame):
        self.video = video
        self.coordinates_data = coordinates
        self.start_frame = start_frame
        self.contours = []
        self.bounds = []
        self.mask = []

    def alpr_call(self):
        
        alpr()
    
    def detect_motion(self):
        
        y=0
        f= open("config.txt","r")
        arr = {}
        for _ in range(0,2):
            result = f.readline()
            arr[result.split(' : ')[0]] = result.split(' : ')[-1].split('\n')[0]
        print(arr)
        f.close()
        url=arr['img_url']
        
        position_in_seconds=0
        coordinates_data = self.coordinates_data
        logging.debug("coordinates data: %s", coordinates_data)
        

        for p in coordinates_data:
            coordinates = self._coordinates(p)
            logging.debug("coordinates: %s", coordinates)

            rect = open_cv.boundingRect(coordinates)
            logging.debug("rect: %s", rect)

            new_coordinates = coordinates.copy()
            new_coordinates[:, 0] = coordinates[:, 0] - rect[0]
            new_coordinates[:, 1] = coordinates[:, 1] - rect[1]
            logging.debug("new_coordinates: %s", new_coordinates)

            self.contours.append(coordinates)
            self.bounds.append(rect)

            mask = open_cv.drawContours(
                np.zeros((rect[3], rect[2]), dtype=np.uint8),
                [new_coordinates],
                contourIdx=-1,
                color=255,
                thickness=-1,
                lineType=open_cv.LINE_8)

            mask = mask == 255
            self.mask.append(mask)
            logging.debug("mask: %s", self.mask)

        statuses = [False] * len(coordinates_data)
        times = [None] * len(coordinates_data)

        while True:
            img_resp= requests.get(url)
            img_arr= np.array(bytearray(img_resp.content),dtype=np.uint8)
            img = open_cv.imdecode(img_arr, -1)
            scale_percent = 60 # percent of original size
            width = int(img.shape[1] * scale_percent / 150)
            height = int(img.shape[0] * scale_percent / 150)
            dim = (width, height)

            # resize image
            resized = open_cv.resize(img, dim, interpolation = open_cv.INTER_AREA)\
            frame = img
            result=True

            blurred = open_cv.GaussianBlur(frame.copy(), (5, 5), 3)
            grayed = open_cv.cvtColor(blurred, open_cv.COLOR_BGR2GRAY)
            new_frame = frame.copy()
            logging.debug("new_frame: %s", new_frame)
            position_in_seconds+=1


            for index, c in enumerate(coordinates_data):
                status = self.__apply(grayed, index, c)

                if times[index] is not None and self.same_status(statuses, index, status):
                    times[index] = None
                    continue

                if times[index] is not None and self.status_changed(statuses, index, status):
                    if position_in_seconds - times[index] >= MotionDetector.DETECT_DELAY:
                        statuses[index] = status
                        y=index
                        
                        print(str(index+1)+"  :"+str(status))
                        if status == False:
                            f= open("file.txt","w+")
                            f.write('%d ' % index)
                            flag=1
                            f.write('%d' % flag)
                            f.close()

                            #   dump it in the file
                            '''temp = points[y]temp
                            q=temp['coordinates']
                            r=[q[0][0],q[1][0],q[2][0],q[3][0]]
                            x_max=max(r)
                            x_min=min(r)
                            r=[q[0][1],q[1][1],q[2][1],q[3][1]]
                            y_min=min(r)
                            y_max=max(r)
                            cropped_image = new_frame[y_min:y_max,x_min:x_max]
                            #open_cv.imshow("Cropped",cropped_image)
                            open_cv.imwrite('image.jpg',cropped_image)'''
                            
                        else:

                            f= open("file.txt","w+")
                            f.write('%d ' % index)
                            flag=2
                            f.write('%d' % flag)
                            f.close()

                        alpr_thread = threading.Thread(target=self.alpr_call,args=[])
                        alpr_thread.start()
                        times[index] = None
                    continue

                if times[index] is None and self.status_changed(statuses, index, status):
                    times[index] = position_in_seconds
             

                
                

            for index, p in enumerate(coordinates_data):
                coordinates = self._coordinates(p)
                
                if statuses[index]:
                    color = COLOR_YELLOW
                    
                else:
                    color = COLOR_PINK
                                                        
                draw_contours(new_frame, coordinates, str(p["id"] + 1), COLOR_WHITE, color)

            open_cv.imshow("img",new_frame)
            k = open_cv.waitKey(1)
            if k == ord("q"):
                break
        open_cv.destroyAllWindows()
        alpr_thread.join()

    


    def __apply(self, grayed, index, p):
        coordinates = self._coordinates(p)
        logging.debug("points: %s", coordinates)

        rect = self.bounds[index]
        logging.debug("rect: %s", rect)

        roi_gray = grayed[rect[1]:(rect[1] + rect[3]), rect[0]:(rect[0] + rect[2])]
        laplacian = open_cv.Laplacian(roi_gray, open_cv.CV_64F)
        logging.debug("laplacian: %s", laplacian)

        coordinates[:, 0] = coordinates[:, 0] - rect[0]
        coordinates[:, 1] = coordinates[:, 1] - rect[1]

        status = np.mean(np.abs(laplacian * self.mask[index])) < MotionDetector.LAPLACIAN
        logging.debug("status: %s", status)

        return status

    @staticmethod
    def _coordinates(p):
        return np.array(p["coordinates"])

    @staticmethod
    def same_status(coordinates_status, index, status):
        return status == coordinates_status[index]

    @staticmethod
    def status_changed(coordinates_status, index, status):
        return status != coordinates_status[index]


class CaptureReadError(Exception):
    pass


    

    
