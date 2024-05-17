#!/usr/bin/python3

import os
import xmltodict
import json
import requests
from requests.auth import HTTPDigestAuth
import datetime
import time

#tvheadend_ip="192.168.8.212"
tvheadend_ip="192.168.5.5"
tvheadend_port="9981"
tvheadend_user=""
tvheadend_pass=""

if "TVHEADEND_IP" in os.environ:
    tvheadend_ip=os.environ["TVHEADEND_IP"]

if "TVHEADEND_PORT" in os.environ:
    tvheadend_port=os.environ["TVHEADEND_PORT"]

if "TVHEADEND_USER" in os.environ:
    tvheadend_user=os.environ["TVHEADEND_USER"]

if "TVHEADEND_PASS" in os.environ:
    tvheadend_pass=os.environ["TVHEADEND_PASS"]

log_time_stack=[]

def log_indent():
    global log_time_stack
    l=len(log_time_stack)
    return "│ "*l

def log_start(text):
    global log_time_stack
    indent=log_indent()
    log_time_stack.append(time.time())
    print(indent+"┌"+text)

def log(text):
    global log_time_stack
    indent=log_indent()
    print(indent+" "+text)

def log_end(text):
    global log_time_stack
    d=time.time()-log_time_stack.pop()
    indent=log_indent()
    if text=="":
        text="done"
    print(indent+"└▶"+format_delta(d)+" "+text);

def format_delta(delta):
    a=abs(delta) 
    if a>60:
        return str(datetime.timedelta(seconds=int(a)))
    if a>1:
        return "{:0.5}".format(delta)+"s"
    if a>0.001:
        return "{:0.5}".format(delta*1000)+"ms"
    return "{:0.5}".format(delta*1000000)+"µs"

def download_json(url, auth):
    req=requests.get(url, auth=auth)
    req.encoding="UTF-8"
    if req.status_code != 200:
        print("Couldn't get JSON data form tvheadendt. Maybe user has insufficient rights. Code: ", req.status_code)
        exit()
    return json.loads(req.text)



log_start("Gathering data")

base_url="http://"+tvheadend_ip+":"+tvheadend_port+"/"
base_url_auth="http://"+tvheadend_user+":"+tvheadend_pass+"@"+tvheadend_ip+":"+tvheadend_port+"/"
auth=HTTPDigestAuth(tvheadend_user, tvheadend_pass)

log_start("downloading muxes from tvheadend");
dvb_muxes=download_json(base_url+"api/raw/export?class=dvb_mux", auth)
log_end("%s muxes"%(len(dvb_muxes)))

log_end("")

log_start("Finding double muxes")
muxes_to_delete=[]
for mux in dvb_muxes:
    if mux["uuid"] in muxes_to_delete:
        continue
    index=dvb_muxes.index(mux)
    for n in range(index+1, len(dvb_muxes)):
        mux2=dvb_muxes[n]
        differences=0
        for prop in ["delsys", "frequency", "symbolrate", "polarisation", "modulation", "fec", "stream_id", "pls_mode", "pls_code", "orbital"]:
            if prop in mux and prop in mux2:
                if mux[prop]!=mux2[prop]:
                    differences=differences+1
            if differences>0:
                break
        if differences==0:
            if not mux2["uuid"] in muxes_to_delete:
                muxes_to_delete.append(mux2["uuid"])
log_end("Found %s double muxes"% (len(muxes_to_delete)))


log_start("Applying changes to tvheadend")
log_start("Deleting %s double muxes" % (len(muxes_to_delete)))
batch=[]
for m in muxes_to_delete:
    req=requests.post("http://"+tvheadend_ip+":"+tvheadend_port+"/api/idnode/delete", data={'uuid':[m]}, auth=HTTPDigestAuth(tvheadend_user, tvheadend_pass))
    req.encoding="UTF-8"
    log(m+" "+str(req.status_code)+" "+req.text)
log_end("");


log_end("")
