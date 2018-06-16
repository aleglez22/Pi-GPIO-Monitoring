from flask import Blueprint, render_template, jsonify, request, url_for, redirect
from flask.ext.login import login_required
import os
from config import UPDATE_CHECK_URL, UPDATE_DESTINATION_DIR, UPDATE_DOWNLOAD_URL
from wcomartin.update import Update
from wcomartin.server import Server
import requests
import requests.exceptions
import logging
import re
import shutil
import subprocess
import tarfile
import RPi.GPIO as GPIO
from models import Gpioinfo
from database import db
from time import sleep, time
import StringIO
import csv
from flask import make_response
import json
import datetime


#COMMENT
version_re = re.compile('version=(?P<version>[0-9.]+)')

mod = Blueprint('gpioController',
                __name__,
                template_folder='templates',
                static_folder='static')


debounce=100 #time to debounce GPIO input 


def updateGpioDatabase(gpionumber):
    pin = Gpioinfo.query.filter_by(gpionumber=gpionumber).first()
    previous_state=pin.state
    pin.state=GPIO.input(gpionumber)
    if previous_state and not pin.state:
        pin.count+=1
    db.session.commit()
    GPIO.remove_event_detect(gpionumber)# this is needed because of a RPI.GPIO bug 
    GPIO.add_event_detect(gpionumber, GPIO.BOTH, callback=updateGpioDatabase, bouncetime=debounce)

@mod.route('/')
@login_required
def gpio_index():
    pinList= Gpioinfo.query.order_by(Gpioinfo.id).all()
    lastDate=pinList[0].date
    lastDate= lastDate.strftime("%Y-%m-%d %H:%M:%S")
    configure()
    return render_template('gpio.jinja', pins=pinList, lastDate=lastDate, debounce=debounce)

#sets the bounce time for all interrupt events
@mod.route('/setDebounce', methods=['POST'])
@login_required
def setDebounce():
    bounce=int(request.form['bounce_time'])
    global debounce
    debounce = bounce
    return redirect(url_for('gpioController.gpio_index'))

@mod.route('/press/<pinNumber>', methods=['POST'])
@login_required
def gpio_press(pinNumber):
    pin = Gpioinfo.query.filter_by(gpionumber=pinNumber).first()
    pin.description = request.form['txtDescription']
    pin.enabled = int(request.form['txt_enabled'])
    db.session.commit()
    return redirect(url_for('gpioController.gpio_index'))

#not needed
@mod.route('/startMonitoring')
@login_required
def startMonitoring():
    configure()
    return redirect(url_for('gpioController.gpio_index'))

#Exports data to csv file
@mod.route('/export')
@login_required
def export():
    si = StringIO.StringIO()
    cw = csv.writer(si)
    exportDate=datetime.datetime.utcnow()
    exportDate=exportDate.strftime("%Y-%m-%d %H:%M:%S")
    myData=[["GPIO","Description","State","Count", "Exported:"+str(exportDate)]]

    for row in Gpioinfo.query.order_by(Gpioinfo.id).all():
        line=[]
        line.append(str(row.gpionumber))
        line.append(str(row.description))
        line.append(str(row.state))
        line.append(str(row.count))
        line.append(str(row.date))
        myData.append(line)
    print (myData)

    cw.writerows(myData)
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

#clears counters and save the cleared datetime
@mod.route('/clearCounters')
@login_required
def clearCounters():
    for row in Gpioinfo.query.all():
        row.count=0
        row.date= datetime.datetime.utcnow()
        db.session.commit()
    return redirect(url_for('gpioController.gpio_index'))


#returns counts and states of GPIO to Ajax refresh data
@mod.route('/statusAndCount', methods=['POST', 'GET'])
@login_required
def statusAndCount():
    data=[]
    enabledPins = Gpioinfo.query.filter_by(enabled=0).order_by(Gpioinfo.id)
    for row in enabledPins:
        objeto={}
        objeto["gpionumber"]= row.gpionumber
        objeto["count"]= row.count
        objeto["state"]= row.state
        data.append(objeto)
    return json.dumps(data)


#Sets BCM mode and add event_detect to enabled GPIOs 
def configure():
    start=time()
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    enabledPins = Gpioinfo.query.filter_by(enabled=0).order_by(Gpioinfo.id)
    try:
        for pin in enabledPins:
            pinNumber=pin.gpionumber
            GPIO.setup(pinNumber, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            pin.state=GPIO.input(pinNumber)
            GPIO.add_event_detect(pinNumber, GPIO.BOTH, callback=updateGpioDatabase, bouncetime=debounce)
            db.session.commit()
    except Exception as e:
        print("conf error "+str(e))
    finally:
        pass
    print("it took "+ str(time()- start))