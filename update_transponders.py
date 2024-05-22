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
log_start("Get tuxtxt satellites.xml")
log_start("Downloading")
req=requests.get("https://raw.githubusercontent.com/OpenPLi/tuxbox-xml/master/xml/satellites.xml")
req.encoding="UTF-8"
if req.status_code > 299:
    log_end("Couldn't get multiplex list. Maybe user has insufficient rights. Code: %s" % (req.status_code))
    exit()
log_end("Done. Stauts-Code: %s" %(req.status_code))
log_start("Parsing")
satellite_document=xmltodict.parse(req.text)["satellites"]["sat"]
log_end("Done. %s satellites" % (len(satellite_document)))
log_end("")

base_url="http://"+tvheadend_ip+":"+tvheadend_port+"/"
base_url_auth="http://"+tvheadend_user+":"+tvheadend_pass+"@"+tvheadend_ip+":"+tvheadend_port+"/"
auth=HTTPDigestAuth(tvheadend_user, tvheadend_pass)

log_start("downloading muxes from tvheadend");
dvb_muxes_=download_json(base_url+"api/raw/export?class=dvb_mux", auth)
log_end("%s muxes"%(len(dvb_muxes_)))

dvb_muxes=[]
dvb_muxes_failed=[]
log_start("Sorting Muxes into failed and OK")
for x in dvb_muxes_:
    if not 'orbital' in x:
        continue
    if x["scan_result"]==2 and len(x["services"])==0:
        dvb_muxes_failed.append(x["uuid"])
    pos=0
    if 'orbital' in x:
        orbital=x["orbital"]
        if len(orbital)>2:
            pos=float(orbital[0:-1])
            if orbital[-1]=="W":
                pos=-pos
        dvb_muxes.append([x, pos])
log_end("failed muxes: %s; ok muxes: %s" %(len(dvb_muxes_failed),len(dvb_muxes)))

log_start("Getting tvheadend network data")
networks=download_json(base_url+"api/raw/export?class=dvb_network", auth)
log_end("got %s networks"% (len(networks)))

log_end("")

log_start("enumerating used positions")
positions=[]
for x in networks:
    if 'orbital_pos' in x:
        orbital=x["orbital_pos"]
        pos=float(orbital[0:-1])
        if orbital[-1]=="W":
            pos=-pos
        positions.append([pos,x["uuid"],x["networkname"]])
log_end("%s positions" %(len(positions)))

log_start("ennumerating transponders")
transponders={}
for sat in satellite_document:
    pos=float(sat["@position"])/10
    min_p=None
    min_dif=999999
    for p in positions:
        dif=abs(p[0]-pos)
        if dif<min_dif:
            min_dif=dif
            min_p=p
    if min_dif>1.5:
        continue

    if 'transponder' in sat:
        for trans in sat['transponder']:
            if type(trans)==str:
                continue
            t_name=str(pos)
            t={}
            for t_property in trans:
                t_value=trans[t_property]
                if t_property == "@frequency":
                    t["frequency"]=int(t_value)
                    t_name=t_name+"-"+t_value
                    continue
                if t_property == "@symbol_rate":
                    t["symbolrate"]=int(t_value)
                    t_name=t_name+"-"+t_value
                    continue
                if t_property == "@polarization":
                    t_name=t_name+"-"+t_value
                    if t_value == "1":
                        t["polarisation"]="V"
                    if t_value == "0":
                        t["polarisation"]="H"
                    continue
                if t_property == "@fec_inner":
                    if t_value == "1":
                        t["fec"]="1/2"
                    if t_value == "2":
                        t["fec"]="2/3"
                    if t_value == "3":
                        t["fec"]="3/4"
                    if t_value == "4":
                        t["fec"]="5/6"
                    if t_value == "5":
                        t["fec"]="7/8"
                    if t_value == "6":
                        t["fec"]="8/9"
                    if t_value == "7":
                        t["fec"]="3/5"
                    if t_value == "9":
                        t["fec"]="9/10"
                    if t_value == "10":
                        t["fec"]="6/7"
                    continue
                if t_property == "@system":
                    if t_value == "0":
                        t["delsys"]="DVB-S"
                    if t_value == "1":
                        t["delsys"]="DVB-S2"
                    continue
                if t_property == "@modulation":
                    if t_value == "1":
                        t["modulation"]="QPSK"
                    if t_value == "2":
                        t["modulation"]="PSK/8"
                    if t_value == "4":
                        t["modulation"]="16APSK"
                    continue
                if t_property == "@pls_mode":
                    if t_value == "1":
                        t["pls_mode"]="GOLD"
                    else:
                        t["pls_mode"]="ROOT"
                    continue
                if t_property == "@is_id":
                    t["stream_id"]=int(t_value)
                    continue
                if t_property == "@pls_code":
                    t["pls_code"]=int(t_value)
                    continue
                #print(t_property+"="+t_value)
            if t["frequency"]<8000000: #No C-Band
                continue
            if t["frequency"]>13000000: #No Ku-Band
                continue
            tr={}
            tr["data"]=t
            tr["uuid"]=min_p[1]
            tr["pos"]=min_p[0]
            transponders[t_name]=tr

log_end("%s transponders found in satellites.xml" % (len(transponders)))

log_start("Finding existing muxes for transponders")
delete_transponders=[]
for tn in transponders:
    t=transponders[tn]
    for m in dvb_muxes:
        if abs(t["pos"]-m[1])>1.5:
            continue
        t_data=t["data"]
        m_data=m[0]
        dif=0
        for prop in t_data:
            if prop=="frequency":
                continue
            if not prop in m_data:
                dif=dif+1
                break
            if t_data[prop]!=m_data[prop]:
                dif=dif+1
                break
        if dif>0:
            continue
        fdiff=abs(t_data["frequency"]-m_data["frequency"])
        if (fdiff>1000):
            continue        
        delete_transponders.append(tn)
        if m_data["uuid"] in dvb_muxes_failed:
            dvb_muxes_failed.remove(m_data["uuid"])
log_end("Found %s muxes for transponders" % (len(delete_transponders)))

log_start("Filtering %s transponders" % (len(transponders)))
for t in delete_transponders:
    if t in transponders:
        transponders.pop(t)
log_end("%s transponders left" % (len(transponders)))

#exit()

log_start("Applying changes to tvheadend")
log_start("Deleting %s failed muxes"% (len(dvb_muxes_failed)))
for uuid in dvb_muxes_failed:
    req=requests.post("http://"+tvheadend_ip+":"+tvheadend_port+"/api/idnode/delete", data={'uuid':[uuid]}, auth=HTTPDigestAuth(tvheadend_user, tvheadend_pass))
    req.encoding="UTF-8"
    log(uuid+" "+str(req.status_code)+" "+req.text)
log_end("");

log_start("Adding new %s muxes" % (len(transponders)))
for tn in transponders:
    t=transponders[tn]
    post_data={}
    post_data['uuid']=t['uuid']
    post_data["conf"]=json.dumps(t['data'])
    req=requests.post("http://"+tvheadend_ip+":"+tvheadend_port+"/api/mpegts/network/mux_create", data=post_data, auth=HTTPDigestAuth(tvheadend_user, tvheadend_pass))
    req.encoding="UTF-8"
    log(str(t["pos"])+" "+json.dumps(t['data'])+" "+str(req.status_code)+" "+req.text)
log_end(" %s muxes added" % (len(transponders)))


log_end("")
