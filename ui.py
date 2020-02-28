#!/usr/bin/env python3

# Code here based off of the tutorial at https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/
# Changed to allow for multiple streams, beyond just video
# Enter address 127.0.0.1:8000 in browser to watch stream

# Run with command: python webstreaming.py

# Pipeline
#   Input from sensors_threads.py

# import the necessary packages
import threading, datetime, imutils, time, random, copy, socketserver, json, socket

import numpy as np
from flask import Response
from flask import Flask
from flask import render_template
from imutils.video import VideoStream
import cv2

def main(server=False):
    # Initialize the dictionary containing our sensor values

    global sensor_dict, lock, vs

    sensor_dict = {
        "frame": None,
        "us_front": None,
        "us_left": None,
        "us_right": None,
        "a": None,
        "m": None
        }

    # Lock to share among threads
    lock = threading.Lock()
     
    # initialize a flask object
    app = Flask(__name__)
     
    # initialize the video stream and allow the camera sensor to
    # warmup
    #vs = VideoStream(usePiCamera=1).start()
    vs = VideoStream(src=0).start()
    time.sleep(2.0)

    class Handler_UDPServer(socketserver.BaseRequestHandler):

        def handle(self):
            # Grab global vars
            global sensor_dict, lock

            # Receive data from UDP client
            self.data = self.request[0].strip() ##remove leading and ending whitespace
            #self.data = self.myreceive()

            # Decode data dictionary
            data_dict = json.loads(self.data)
            if data_dict["frame"] is not None:
                data_dict["frame"] = np.asarray(data_dict["frame"], dtype=np.uint8)

            # Write data dictionary with lock
            with lock:
                for data_key in data_dict:
                    sensor_dict[data_key] = data_dict[data_key]

    class Handler_TCPServer(socketserver.StreamRequestHandler):

        def handle(self):
            # Grab global vars
            global sensor_dict, lock

            while True:

                # Receive data from UDP client
                self.data = self.rfile.readline().strip() ##remove leading and ending whitespace

                # Decode data dictionary
                data_dict = json.loads(self.data)
                if data_dict["frame"] is not None:
                    data_dict["frame"] = np.asarray(data_dict["frame"], dtype=np.uint8)

                # Write data dictionary with lock
                with lock:
                    for data_key in data_dict:
                        sensor_dict[data_key] = data_dict[data_key]

    @app.route("/")
    def index():
        # Html shown on screen for UI
        return render_template("index.html")

    def fetch_loop(fetch_func):
        # To be used as a thread
        # Loop over sensor fetch function to grab all sensors
        while True:
            fetch_func()

    def fetch_sensors_server():
        # To be used as a thread
        # Grabs all the sensor values

        # Host address and port number
        HOST, PORT = "localhost", 9000

        socketserver.TCPServer.allow_reuse_address = True
        tcp_server = socketserver.TCPServer((HOST, PORT), Handler_TCPServer)

        tcp_server.serve_forever()

    def fetch_sensors():
        # Grabs all the sensor values

        # Grab global vars
        global vs, sensor_dict, lock

        # Grab a frame from the camera stream
        frame = vs.read()
        frame = imutils.resize(frame, width=400)

        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()
        cv2.putText(frame, timestamp.strftime(
            "%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        flag, frame = cv2.imencode(".jpg", frame)

        # acquire the lock, set the sensor dictionary, and release the
        # lock
        with lock:
            sensor_dict["frame"] = copy.deepcopy(frame)
            sensor_dict["us_front"] = random.randint(0,100)
            sensor_dict["us_left"] = random.randint(0,100)
            sensor_dict["us_right"] = random.randint(0,100)
            sensor_dict["a"] = random.randint(0,100)
            sensor_dict["m"] = random.randint(0,100)

    @app.route("/video_feed")
    def video_feed():
        # Handles the video feed
        # Slightly different from the other feed functions. Generates multipart response

        def generate():
            # grab global references sensor dictionary and lock variables
            global sensor_dict, lock
         
            # loop over frames from the output stream
            while True:
                # wait until the lock is acquired
                with lock:
                    # check if the output frame is available, otherwise skip
                    # the iteration of the loop
                    if sensor_dict["frame"] is None:
                        continue

                    encodedImage = copy.deepcopy(sensor_dict["frame"])
         
                time.sleep(1/15)
                # yield the output frame in the byte format
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
                    bytearray(encodedImage) + b'\r\n')

        # return the response generated along with the specific media
        # type (mime type)
        return Response(generate(),
            mimetype = "multipart/x-mixed-replace; boundary=frame")

    @app.route("/sensor_feed", endpoint="sensor_feed")
    def sensor_feed():

        # grab global references to the sensor dictionary and lock variables
        global sensor_dict, lock

        # wait until the lock is acquired
        response_dict = {
            "us_front": "No sensor read",
            "us_left": "No sensor read",
            "us_right": "No sensor read",
            "a": "No sensor read",
            "m": "No sensor read"
        }        
        with lock:
            # check if the sensor is available, otherwise skip
            # the iteration of the loop
            for key in response_dict.keys():
                if sensor_dict[key] is not None:
                    response_dict[key] = str(sensor_dict[key])

        # return the response generated along with the specific media
        # type (mime type)
        return Response(json.dumps(response_dict), mimetype = "application/json")

    # start a thread that will update sensor dictionary to contain current values
    # Use fetch_sensors function as arg to simulate data. Otherwise, use fetch_sensors_server
    if server:
        t = threading.Thread(target=fetch_loop, args=(fetch_sensors_server,))
        t.daemon = True
        t.start()
    else:
        t = threading.Thread(target=fetch_loop, args=(fetch_sensors,))
        t.daemon = True
        t.start()
 
    # start the flask app
    app.run(host="127.0.0.1", port=8000, debug=True,
        threaded=True, use_reloader=False)

    # release the video stream pointer
    vs.stop()

if __name__ == '__main__':
    main()

