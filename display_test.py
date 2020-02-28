#!/usr/bin/env python3

import threading
import datetime
import time
import random
import copy
import socketserver
import json
import socket
import base64

# import the necessary packages
from flask import Response
from flask import Flask
from flask import render_template
import imutils
from imutils.video import VideoStream
import cv2
import numpy as np

def main(server=False):

    # Set global variables
    global data_feed_dict, lock, vs, update_data_frequency, grid_size

    # Fed to UI
    data_feed_dict = {
        "connection_status": None,
        "us_left": None,
        "us_front": None,
        "us_right": None,
        "position": None,
        "orientation": None,
        "magnetometer": None,
        "videostream": None,
        "mapping": None
    }
    grid_size = 20
    lock = threading.Lock() # Lock shared by data serving thread and data creation thread
    vs = VideoStream(src=0).start() # Video stream to use. In this case it is the laptop webcam
    time.sleep(2)
    update_data_frequency = 10

    def get_frame_generator():

        # Make counter and generic frame
        frame = np.zeros(shape=(250, 400, 3), dtype=np.uint8)
        gen_count = 0
        while True:

            # Increment or reset counter
            if gen_count > 30:
                gen_count = 0
            else:
                gen_count += 1

            # Decide what color the frame should be
            if gen_count < 15:
                frame[:,:,0] = 255
            else:
                frame[:,:,0] = 0

            encode_flag, jpg_frame = cv2.imencode(".jpg", frame)

            img_str = "<img src=\"data:image/jpg;base64,{}\">".format(base64.b64encode(jpg_frame).decode())
            yield img_str

    def get_frame_generator_2():

        global vs

        while True:
            # Grab a frame from the camera stream
            frame = vs.read()
            frame = imutils.resize(frame, width=400)

            # grab the current timestamp and draw it on the frame
            timestamp = datetime.datetime.now()
            cv2.putText(frame, timestamp.strftime(
                "%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

            flag, frame = cv2.imencode(".jpg", frame)

            img_str = "<img src=\"data:image/jpg;base64,{}\">".format(base64.b64encode(frame).decode())
            yield img_str

    def get_mapping_generator():

        while True:

            mapping = np.zeros(shape=(20, 20), dtype=np.uint8)
            mapping[0,:] = 1
            yield convert_map_to_rectangles(mapping)

    def convert_map_to_rectangles(mapping):

        global grid_size
        
        rectangles_dict = {}

        rectangle_count = 0
        for i in range(mapping.shape[0]):
            for j in range(mapping.shape[1]):
                rectangles_dict["rect{}".format(rectangle_count)] = {}
                rectangles_dict["rect{}".format(rectangle_count)]["x"] = i * grid_size
                rectangles_dict["rect{}".format(rectangle_count)]["y"] = j * grid_size
                rectangles_dict["rect{}".format(rectangle_count)]["width"] = grid_size
                rectangles_dict["rect{}".format(rectangle_count)]["height"] = grid_size
                if mapping[i, j] == 0:
                    rectangles_dict["rect{}".format(rectangle_count)]["clear"] = True
                else:
                    rectangles_dict["rect{}".format(rectangle_count)]["clear"] = False

                rectangle_count += 1

        rectangles_dict["n_rectangles"] = rectangle_count

        return rectangles_dict


    def update_data_feed():
        global data_feed, lock, vs, update_data_frequency

        generate_frame = get_frame_generator()
        generate_mapping = get_mapping_generator()

        while True:
            with lock:
                data_feed_dict["connection_status"] = "Connected"
                data_feed_dict["us_left"] = random.randint(0, 100)
                data_feed_dict["us_front"] = random.randint(0, 100)
                data_feed_dict["us_right"] = random.randint(0, 100)
                data_feed_dict["position"] = {
                                            "x": 200,
                                            "y": 200
                                            }
                data_feed_dict["orientation"] = 0;
                data_feed_dict["magnetometer"] = random.randint(0, 100)
                data_feed_dict["videostream"] = next(generate_frame)
                data_feed_dict["mapping"] = next(generate_mapping)

            time.sleep(1/update_data_frequency)

    # initialize a flask object
    app = Flask(__name__)

    @app.route("/")
    def index():
        # Html shown on screen for UI
        return render_template("index.html")

    @app.route("/data_feed")
    def data_feed():
        global data_feed_dict, lock

        with lock:
            return Response(json.dumps(data_feed_dict), mimetype = "application/json")
 
    t = threading.Thread(target=update_data_feed)
    t.daemon = True
    t.start()

    # start the flask app
    app.run(host="127.0.0.1", port=8000, debug=True,
        threaded=True, use_reloader=False)

if __name__ == '__main__':
    main()

