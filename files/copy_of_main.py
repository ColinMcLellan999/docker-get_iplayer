from flask import Flask, render_template, redirect, request,session,make_response,jsonify
import requests
import json
import datetime
import time
import os
# import random
import sys
from google.cloud import storage
from google.cloud.exceptions import NotFound
import polyline
import math
import syncradio


app = Flask(__name__)
app.secret_key = 'a slug eating lettuce is fast and bulbous'
# Assume running in gcloud
debug = False
port = 80
gcloud = True
client_id = "41065"
client_secret = "3902c00ea1b1c2673c6d114191c5f1723c107a85"
#host = "straview.uk.to"
#host = "straview.oa.r.appspot.com"
# host = "straview.com"
# hosturl = "https://straview.com"
host = "straview3.appspot.com"
hosturl = "https://straview3.appspot.com"

if (len(sys.argv) > 1 and sys.argv[1] == "prod"):
    host = "localhost"
    debug = False
    port = 80
    gcloud = False
elif (len(sys.argv) > 1 and sys.argv[1] == "dev"):
    host = "straview.uk.to"
    hosturl = "http://straview.uk.to"
    debug = True
    port = 80
    gcloud = False
    client_id = "54603"
    client_secret = "b07bec06258ecb8870ab9950af40b2a2066974fd"
if gcloud:
    try:
        gcstorage_client = storage.Client()
        gcbucket = gcstorage_client.bucket("straview3.appspot.com")
    except:
        print("\n CANNOT connect to gcloud")

# random.seed()
# redirecturl = "https://www.strava.com/oauth/authorize?client_id=" + client_id + "&redirect_uri=https://" + host + ":" + str(port) + "/login2&response_type=code&scope=read,activity:read_all&approval_prompt=auto&state=private"
redirecturl = "https://www.strava.com/oauth/authorize?client_id=" + client_id + "&redirect_uri=" + hosturl + "/login2&response_type=code&scope=read,activity:read_all&approval_prompt=auto&state=private"
# print("Will use this to redirect:",redirecturl)

progress = {}



################################################################
def putStringFile(s, file):
    if (gcloud):
        blob = gcbucket.blob(file)
        blob.upload_from_string(s)
    else:
        with open(file, 'w') as outfile:
            outfile.write(s)

################################################################
def getStringFile(file):
    s = ""
    try:
        if (gcloud):
            # print ("reading: " + "https://storage.googleapis.com/straview3.appspot.com/" + file)
            blob = gcbucket.blob(file)
            s = (blob.download_as_string()).decode(encoding='UTF-8')
        else:
            with open(file,'r') as sfile:
                s = sfile.read()
    except:
        pass
    return s

################################################################
def fileExist(file):
    exist = False
    try:
        if (gcloud):
            # print ("reading: " + "https://storage.googleapis.com/straview.appspot.com/" + file)
            blob = gcbucket.blob(file)
            exist = blob.exists()
        else:
            exist = os.path.exists(file)
    except:
        pass
    return exist

################################################################
def makeDir(dir):
    if (gcloud):
        pass
    else:
        try:
            os.mkdir(dir)
        except:
            pass

################################################################
def get_strava_tokens():
    try:
        stravaid = session['stravaid']
        file = 'data/strava_tokens_' + str(stravaid) + '.json'
        if (gcloud):
            blob = gcbucket.blob(file)
            strava_tokens = json.loads(blob.download_as_string())
        else:
            with open(file) as json_file:
                strava_tokens = json.load(json_file)

        ## If access_token has expired then use the refresh_token to get the new access_token
        if strava_tokens['expires_at'] < time.time():
        #Make Strava auth API call with current refresh token
            response = requests.post(
                                url = 'https://www.strava.com/oauth/token',
                                data = {
                                        'client_id': client_id,
                                        'client_secret': client_secret,
                                        'grant_type': 'refresh_token',
                                        'refresh_token': strava_tokens['refresh_token']
                                        }
                            )

        #Save response as json in new variable
            strava_tokens = response.json()
        # Save new tokens to file
            putStringFile(json.dumps(strava_tokens), 'data/strava_tokens_' + str(session["stravaid"]) + '.json')
    except:
        return None
    
    return strava_tokens

################################################################
def deleteFile(file):
    if (gcloud):
        try:
            gcbucket.delete_blob(file)
        except NotFound:
            pass
    else:
        if os.path.exists(file): 
            os.remove(file)


################################################################
@app.route("/<any(plain, jquery, fetch):js>")
def fetch(js):
     return render_template("fetch.html".format(), js=js)


##############################################################
def setProgress(s):
    progress[session["stravaid"]] = s

#################################################################
# Get the progress - as an API call
@app.route("/get_progress", methods=["POST","GET"])
def get_progress():
    if session["stravaid"] in progress:
        p = progress[session["stravaid"]]
    else:
        p = ""
        progress[session["stravaid"]] = p
    return p

#################################################################
# Get all the detailed activities - as an API call
@app.route("/get_details", methods=["POST","GET"])
def getdetails():
    # store this data in a directory for this athlete
    makeDir ('data/' + str(session["stravaid"]))

    setProgress("Fetching Activity List...+ for " + str(session["stravaid"])) 
    _,listActs = getActivities()

    # For each activity, get and store the full details in files
    strava_tokens = get_strava_tokens()
    if (strava_tokens == None):
        return notLoggedIn()

    iact = 0
    goodActs = []
    newActs = 0
    fail = ""
    for act in listActs:
        iact += 1
        fdetail = 'data/' + str(session["stravaid"]) + '/raw_details_' + str(act['id']) + '.json'
        # Only need to get this one if we dont already have it
        if (fileExist(fdetail)):
            goodActs.append(act)
            continue

        setProgress("Fetching Activity: " + str(iact) + " of " + str(len(listActs)) + "...")
        r2 = requests.get("https://www.strava.com/api/v3/activities/"  + str(act['id']) + '?access_token=' + strava_tokens["access_token"] + "&include_all_efforts=true")
        detail = r2.json()
        # An over-limit one looks like this: {"message": "Rate Limit Exceeded", "errors": [{"resource": "Application", "field": "rate limit", "code": "exceeded"}]}
        if ("message" in detail):
            fail = "Failure on activity: " + str(iact) + " " + detail["message"]
            break

        putStringFile(json.dumps(detail),fdetail)
        goodActs.append(act)
        newActs += 1

    putStringFile(json.dumps(goodActs),'data/' + str(session["stravaid"]) + '/list_acts.json')
    return jsonify(collected = fail + " " + str(newActs) + " new collected")

#################################################################
# Sync the google cloud to Drive
@app.route("/syncradio", methods=["POST","GET"])
def sync():
    print("Sync RADIO...")
    syncradio.syncradio() 
    return jsonify("DONE Sync")

#################################################################
# See all the detailed activities - as a rendered page
@app.route("/details", methods=["POST","GET"])
def details():
    if 'stravaid' not in session:
        return redirect("/", code=302)

    disp = " NO ACTIVITIES COLLECTED"
    f = getStringFile('data/' + str(session["stravaid"]) + '/list_acts.json')
    if (len(f) > 0):
        acts = json.loads(f)
        disp = str(len(acts)) + " activities " + acts[-1]["start_date_local"][:10] + " - " + acts[0]["start_date_local"][:10]
    return render_template("details.html", collected=disp)



#################################################################
# Get all the detailed activities - as an API call
# params atype, limit
@app.route("/get_analyse", methods=["POST","GET"])
def get_analyse():
    atype = request.args.get("atype")
    limit = request.args.get("limit")
    ilimit = int(limit)
    print("in analyse on server. " + atype)
    headers = ["id","Date","Type","Title","Best 1km","Best 5km","Best 10km","Overall/PR"]

    rawFields = [
                    [ "Miles", "distance"],
                    [ "Av mph", "average_speed"],
                    [ "Pace /mi", "average_speed"],
                    [ "Elev Gain (m)", "total_elevation_gain"],
                    [ "Moving Hrs", "moving_time"]]

    for f in rawFields:
        headers.append(f[0])

    cells = []
    mapinfo = []
    acts = json.loads(getStringFile('data/' + str(session["stravaid"]) + '/list_acts.json'))
    iact = 0
    for act in acts:
        row = []
        mapi = {}
        detail = json.loads(getStringFile('data/' + str(session["stravaid"]) + '/raw_details_' + str(act['id']) + '.json'))

        # Should really get this from summary file.
        rtype = detail["type"]
        if ("splits_metric" in detail and (rtype == atype or atype == "all")):
            print(act["name"])
            # store map info so that we can display this activity on the map
            mapi["polyline"] = detail["map"]["polyline"]
            # row.append(act["id"])
            row.append(iact)
            row.append(detail["start_date_local"][:10])
            row.append(detail["type"])
            row.append("<a href='https://www.strava.com/activities/" + str(act['id']) + "' target=_blank><img src='/static/strava_icon.svg' style='height:16px' alt='view in strava'/></a>&nbsp;"  + act["name"])
            # Get the best 1 kkm
            splits = detail["splits_metric"]
            # splits = detail["splits_standard"]
            # Array of dicts which collate the best splits for different distances
            best = []
            best1k = {
                "name": "1k",
                "nsplits": 1,
                "nmeters": 1000,
                "best_time": 9999999,
                "best_split1": None,
                "best_split_text": None,
                "dist_offset": 0, # Distance from activity start to the first split
                "dist": 0,
                "secs": 0
                }
            best5k = best1k.copy()
            best5k["name"] = "5k"
            best5k["nsplits"] = 5
            best5k["nmeters"] = 5000

            bestTk = best1k.copy()
            bestTk["name"] = "10k"
            bestTk["nsplits"] = 10
            bestTk["nmeters"] = 10000
            best.append(best1k)
            best.append(best5k)
            best.append(bestTk)

            isplit = 0
            for split in splits:
                isplit += 1
                for ibest in best:
                    # get the rolling best
                    ibest["dist"] += float(split["distance"])
                    ibest["secs"] += float(split["moving_time"])

                    if (isplit > ibest["nsplits"]):
                        # remove the first one from the last rolling best
                        ibest["dist"] -= float(splits[isplit-ibest["nsplits"]-1]["distance"])
                        ibest["secs"] -= float(splits[isplit-ibest["nsplits"]-1]["moving_time"])

                    # Enough distance covered?
                    if (isplit >= ibest["nsplits"] and (ibest["dist"] > (ibest["nmeters"]*0.8))):
                        if (ibest["dist"] < 0.1):
                            ibest["dist"] = 0.1
                        time_adjusted = ibest["secs"] * ibest["nmeters"] / ibest["dist"]
                        # print ("secs,nmeters,dist,best_time,ta",ibest["secs"], ibest["nmeters"],ibest["dist"],ibest["best_time"],time_adjusted, ibest["best_split1"])
                        if (time_adjusted < ibest["best_time"]):
                            ibest["best_time"] = time_adjusted
                            ibest["best_split1"] = isplit-ibest["nsplits"]+1
                            ibest["best_split_text"] = "(" + str(ibest["best_split1"]) + "-" + str(split["split"]) + ")"

            for ibest in best:
                # print ("FINAL secs,nmeters,dist,best_time,ta",ibest["secs"], ibest["nmeters"],ibest["dist"],ibest["best_time"], ibest["best_split1"])
                if (ibest["best_split1"]):
                    val = str(datetime.timedelta(seconds=ibest["best_time"]))[2:7] + ibest["best_split_text"]
                    mapi["poly" + ibest["name"]] = getSplitPoly (detail["map"]["polyline"], ibest["best_split1"], ibest["best_split1"]+ ibest["nsplits"] - 1, splits, detail["distance"])
                else:
                    val = "too short"
                    mapi["poly" + ibest["name"]] = ""
                row.append(val)

            ##################################################
            # Achievements
            noverall = 0
            npr = 0
            if ("segment_efforts" in detail):
                segs = detail["segment_efforts"]
                for seg in segs:
                    for ach in seg["achievements"]:
                        if (ach["type"] == "overall"):
                            noverall += 1
                        if (ach["type"] == "pr" and ach["rank"] == 1):
                            npr += 1
            row.append(str(noverall)+"/"+str(npr))
            ####################################################

            # Append all other random fields
            for field in rawFields:
                val = detail[field[1]]
                if (field[1] == "distance"):
                    val = "{:.1f}".format(float(val)* 0.000621371192)
                if ("Hrs" in field[0]):
                    val = "{:.1f}".format(float(val)/ 3600)
                if ("mph" in field[0]):
                    val = "{:.1f}".format(float(val)* 3600 * 0.000621371192)
                if ("/mi" in field[0]):
                    if (val != 0.0):
                        x = 1.0/(float(val)* 0.000621371192)
                        val = str(datetime.timedelta(seconds=x))[2:7]
                row.append(val)

    


            # Apppend the whole row
            cells.append(row)
            
            
            mapinfo.append(mapi)
            iact +=1
            if (ilimit > 0 and iact >= ilimit):
                break
        
    cells.sort(reverse=False)
    return jsonify({"headers": headers, "cells": cells, "mapinfo": mapinfo})


###############################################################
# get the polyline of the path between the 2 splits
def getSplitPoly (polylinein, split1, split2, splits, tdistance):
    if (polylinein == ""):
        return ""
    coords = polyline.decode(polylinein)
    dist1 = 0.0
    if (split1 > 1):
        for split in splits[:(split1-1)]:
            dist1 += split["distance"]
    dist2 = dist1
    for split in splits[split1-1:split2]:
        dist2 += split["distance"]

    # print ("split between", dist1, dist2)

    path = 0.0
    ipath = 0
    poly1 = 0
    poly2 = 0
    # cosfix = math.cos(coords[0][0])
    for coord in coords[1:]:
        # coords are lat, lng
        # this forula quick but wrong!
        # x = coord[0] - coords[ipath][0]
        # y = (coord[1] - coords[ipath][1])*cosfix
        # path += 110250*math.sqrt(x*x + y*y)
#################################################
# Earth distance formula
        R = 6373000.0
        lat1 = math.radians(coord[0])
        lon1 = math.radians(coord[1])
        lat2 = math.radians(coords[ipath][0])
        lon2 = math.radians(coords[ipath][1])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        path += R * c
#################################################
        ipath += 1
        if (poly1 == 0 and path > dist1):
            poly1 = ipath
        if (poly2 == 0 and path > dist2):
            poly2 = ipath
            break
            
    if (poly2 == 0):
        poly2 = ipath
    # print ("coords are between:", poly1, poly2, "for splits:", split1, split2, "path,tdistance", path, tdistance)
    if (poly2 <= 1):
        return ""
    try:
        return polyline.encode(coords[poly1:poly2])
    except:
        return ""


################################################################
@app.route('/')
def index():
    if 'firstname' in session:
        resp = make_response(render_template('index2.html', name = session['firstname']))
        return resp
    else:
        known = request.cookies.get('known')
        if (known and (known == '1')):
            # we know he has been authorised before so log him in
            return redirect(redirecturl, code=302)

    resp = notLoggedIn()
    return resp 

#https://www.strava.com/oauth/authorize?client_id=36&scope=read,read_all,profile:read_all,profile:write,activity:read,
#activity:read_all,activity:write&redirect_uri=https://veloviewer.com/&response_type=code&approval_prompt=auto&state=private

#############################################################
def notLoggedIn():
    resp = make_response(render_template('index.html', url=redirecturl))
    resp.set_cookie('known', '0', expires=datetime.datetime.now() + datetime.timedelta(days=1000))
    return resp


#########################################################
@app.route('/routes')
def routes():
    if 'stravaid' not in session:
        return redirect("/", code=302)

    strava_tokens = get_strava_tokens()
    if (strava_tokens == None):
        return notLoggedIn()

    # if ('dversion' not in session):
    # session["dversion"] = random.random()
    print("Showing route for:" + session["firstname"])

    # jsource = "/static/routes_" + str(session['stravaid']) + ".js?v=" + str(session['dversion'])
    jfile = "static/routes_" + str(session['stravaid']) + ".js"
    
    jcode = getStringFile(jfile)
    return render_template('poly.html', jcode = jcode)


#########################################################
@app.route('/login')
def login():
    print ("port:" + str(port))
    return redirect(redirecturl, code=302)

#########################################################
@app.route('/login2')
def login2():
    # should get: http://localhost:5001/login2?state=&code=f6ce444973ea0d26bee2b9a11f212099ff76dd8b&scope=read,activity:read_all
    code = request.args.get('code')
    scope = request.args.get('scope')
    if ("activity:read_all" in scope):
        response = requests.post(
                            url = 'https://www.strava.com/oauth/token',
                            data = {
                                    'client_id': client_id,
                                    'client_secret': client_secret,
                                    'code': code,
                                    'grant_type': 'authorization_code'
                                    }
                        )

        #Save json response as a variable
        strava_tokens = response.json()
        if ('message' in strava_tokens):
            #  print(str(strava_tokens['message']))
             return 'ERROR' + str(strava_tokens)

        # print(str(strava_tokens))
        session['stravaid'] = strava_tokens['athlete']['id']
        session['firstname'] = strava_tokens['athlete']['firstname']
        session['photo'] = strava_tokens['athlete']['profile_medium']

        # Need to obfuscate this at a later date
        # Save tokens to file
        putStringFile(json.dumps(strava_tokens), 'data/strava_tokens_' + str(session["stravaid"]) + '.json')
        resp = make_response(render_template('login2.html', name =session['firstname'] ))
        resp.set_cookie('known', '1', expires=datetime.datetime.now() + datetime.timedelta(days=1000))
        return resp
#        return str(data + session['stravaid'])    
    else:
        return 'Require read_all to be checked to use this app - sorry! Go back and and fix if you wish to continue.'


#########################################################
@app.route('/delete')
def delete():
    if 'stravaid' not in session:
        return "NOT PERMITTED"

    deleteFile('data/strava_tokens_' + str(session["stravaid"]) + '.json')
    deleteFile("static/routes_" + str(session["stravaid"]) +".js")
    resp = make_response(render_template('delete.html'))
    resp.set_cookie('known', '0', expires=0)
    session.pop('stravaid',None)
    session.pop('firstname',None)
    return resp



#########################################################
def getActivities():
    if 'firstname' not in session:
        return '*** must be logged in via strava'

    maxactivity = 800
    m = request.args.get('maxactivity')
    if (m):
        maxactivity = int(m)

    ## Get the tokens from file to connect to Strava
    strava_tokens = get_strava_tokens()

    #Loop through all activities
    page = 1
    activity = 0
    url = "https://www.strava.com/api/v3/activities"
    access_token = strava_tokens['access_token']
    ## Create the dataframe ready for the API call to store your activity data
    
    script = "var encodedRoutes = [\n"

    # array to use in the display table
    displayActs = []
    listActs = []
    displayFields = [{"title": "activity number"}]
    # Display v. raw internal
    rawFields = [
                    [ "Date",       "start_date_local"],
                    [ "Activity",   "name"],
                    [ "Type",        "type"],
                    [ "Miles", "distance"],
                    [ "Av mph", "average_speed"],
                    [ "Pace /mi", "average_speed"],
                    [ "Elev Gain (m)", "total_elevation_gain"],
                    [ "Moving Hrs", "moving_time"],
                    [ "Elapse Hrs", "elapsed_time"],
                    [ "With", "athlete_count"],
                    [ "id", "id"]]
    for f in rawFields:
        displayFields.append({"title": f[0]})

    while True:        
        # get page of activities from Strava
        r = requests.get(url + '?access_token=' + access_token + '&per_page=200' + '&page=' + str(page))
        r = r.json()
    # if no results then exit loop
        if (not r):
            break
        
        # otherwise add new data to dataframe
        
        for act in r:
            # store for later use in performance details
            listActs.append({"id": act['id'], "name": act['name'], "start_date_local": act['start_date_local']})
            # print ("\n$$$$$$$$$ x,len(r)" + str(x) + "," + str(len(r)))
            # print ("\n" + str(r[x]))
            polyline = act["map"]["summary_polyline"]
            # print ("\n***POLY:" + polyline)
            if (polyline):
                popup = str(act['start_date_local']) + "<br/>" + str(act['name'])
                script += '["' + popup + '","' + polyline.replace('\\','\\\\') + '"],\n'
                # First column is hidden field of the sequential activity number
                disp = [str(activity)]
                for field in rawFields:

                    # Do conversions for readability
                    val = act[field[1]]
                    if (field[1] == "name"):
                        val = "<a href='https://www.strava.com/activities/" + str(act['id']) + "' target=_blank><img src='/static/strava_icon.svg' style='height:16px' alt='view in strava'/></a>"  + val
                    if (field[1] == "distance"):
                        val = "{:.1f}".format(float(val)* 0.000621371192)
                    if (field[1] == "start_date_local"):
                        val = val[:10]
                    if ("Hrs" in field[0]):
                        val = "{:.1f}".format(float(val)/ 3600)
                    if ("mph" in field[0]):
                        val = "{:.1f}".format(float(val)* 3600 * 0.000621371192)
                    if ("/mi" in field[0]):
                        if (val != 0.0):
                            x = 1.0/(float(val)* 0.000621371192)
                            val = str(datetime.timedelta(seconds=x))[2:7]
                    if ("With" in field[0]):
                        val = str(int(val) - 1)

                    disp.append(val)
                displayActs.append(disp)



    #ONLY NEED to get the specific journey if we need the accurate polyline
            # r2 = requests.get("https://www.strava.com/api/v3/activities/"  + str(r[x]['id']) + '?access_token=' + access_token + "&include_all_efforts=true")
            # if (r2 and r2.json()["map"] and "summary_polyline" in r2.json()["map"]):
            #     # print ("\nMAP:" + str(r[x]['id']) + " " + str(r2.json()["map"]))  
            #     polyline = r2.json()["map"]["summary_polyline"]
            #     # polyline = r2.json()["map"]["polyline"]
            #     if (polyline):
            #         popup = str(r[x]['start_date_local']) + "<br/>" + str(r[x]['name'])
            #         fscript.write('["' + popup + '","' + polyline.replace('\\','\\\\') + '"],\n')

                activity += 1
                if (activity >= maxactivity):
                    break
            if (activity >= maxactivity):
                break
        if (activity >= maxactivity):
            break
    # increment page
        page += 1

    script += '["",""]\n]\n'

    script += '\ndisplayFields = '
    script += json.dumps(displayFields)

    script += '\ndisplayActs = '
    script += json.dumps(displayActs)
    putStringFile (script,"static/routes_" + str(session["stravaid"]) +".js")
    return displayActs, listActs


#########################################################
@app.route('/refresh')
def refresh():
    getActivities()
    # session['dversion'] = random.random()
    return redirect("/routes", code=302)


#########################################################
if __name__ == '__main__':
    app.run(debug=debug, host='0.0.0.0', port=port)
    # Assume we are in Google Cloud, otherwise run with parameter
    