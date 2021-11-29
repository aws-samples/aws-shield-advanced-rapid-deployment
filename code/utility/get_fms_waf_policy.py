import json
import os
import math
import copy
import random
import datetime
import string

import socket
import struct
import binascii


def scrub(x):
    ret = copy.deepcopy(x)
    # Handle dictionaries. Scrub all values
    if isinstance(x, dict):
        for k,v in ret.items():
            ret[k] = scrub(v)
    # Handle None
    if x == None:
        ret = ""
    # Finished scrubbing
    return ret
def ran_gen(size, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

def qrandom(x):
    return (random.randrange(1,x))

with open('template.json') as template:
    requestTemplate = json.loads(template.read())

with open('ip2country.json') as ip2country:
    ipTable = json.loads(ip2country.read())

with open('standardHeaders.json') as h:
    standardHeaders = json.loads(h.read())
rootURL = "http://dcqqtulaepd1q.cloudfront.net/rest/products/"
request = copy.deepcopy(requestTemplate)

#actual data
#November 9, 2021 8:00:00 PM GMT-05:00
#startTimeEpoch = 1636506000
#November 28, 2021 8:00:00 PM GMT-05:00
#endTimeEpoch = 1638147600

#shorter test range
#August 31, 2021 9:00:00 PM GMT-04:00
startTimeEpoch = 1630458000
#September 14, 2021 9:00:00 PM
endTimeEpoch = 1631667600
tzWindowCount = math.floor((endTimeEpoch - startTimeEpoch)/300)
print (tzWindowCount)

def fake_request(requestTimeStamp, method, headers, userAgents, args, ipDetails, country):
    fakeRequest = copy.deepcopy(requestTemplate)
    httpRequest = fakeRequest['httpRequest']
    fakeRequest['timestamp'] = requestTimeStamp
    httpRequest['requestId'] = ''.join([random.choice(string.ascii_letters+ string.digits) for n in range(32)]) + '=='
    httpRequest['headers'] = headers
    httpRequest['httpMethod'] = method
    httpRequest['headers'].append(
        {
            'name': 'User-Agent',
            'value': userAgents
        })
    httpRequest['httpMethod'] = method
    httpRequest['args'] = args
    httpRequest['clientIp'] = ipDetails['sourceip']
    httpRequest['country'] = ipDetails['country']
    if 'labels' in ipDetails:
        for l in ipDetails['labels']:
            fakeRequest['Labels'] += l
    return (fakeRequest)

def simulate_user(requestTimeStamp, args, country, headers = [], userAgents=[], method = 'GET', labels=[], ipName = 'user', initialURLList = [], minInitial = -1, maxInitial = -1, randomURLList= [], minRandom = 0, maxrandom = 0,finalURLList = [], minFinal = -1, maxFinal = -1):
    requests = []
    l = len(initialURLList)
    if userAgents == []:
        uAgent = ""
    else:
        uAgent = userAgents[random.randrange(0,len(userAgents)-1)]
    if not args == []:
        queryString = random.choice(args)
    else:
        queryString = ""
    ipDetails = source_ip_calculate(ipName, country)
    if minInitial == -1:
        minInitial = l
        maxInitial = l
    if maxInitial == -1:
        maxInitial = l
    if minFinal == -1:
        minFinal == l
        maxFinal == l
    if maxFinal == -1:
        maxFinal == l
    if maxInitial > l:
        maxInitial = l
    if minInitial > l:
        minInitial = l
    if not minInitial == maxInitial:
        y = random.randrange(minInitial,maxInitial)
    else:
        y = maxInitial
    #Make the initial Requests
    if not initialURLList == []:
        for x in range(0,y):
            #Go the general stuff
            request = fake_request(requestTimeStamp, method, headers, uAgent, queryString, ipDetails, country)
            request['httpRequest']['uri'] = rootURL + initialURLList[x]
            #print (request)
            requests.append(copy.deepcopy(request))
        #Make middle random requests
    if not minRandom == maxrandom:
        y = random.randrange(minRandom,maxrandom)
    else:
        y = maxInitial
    if not randomURLList == []:
        for x in range(0,y):
            #Go the general stuff
            request = fake_request(requestTimeStamp, method, headers, uAgent, queryString, ipDetails, country)
            request['httpRequest']['uri'] = random.choice(randomURLList)
            requests.append(copy.deepcopy(request))
    #Make final Requests
    if not minFinal == maxFinal:
        y = random.randrange(minFinal,maxFinal)
    else:
        y = maxFinal
    if not finalURLList == []:
        for x in range(0,y):
            #Go the general stuff
            request = fake_request(requestTimeStamp, method, headers, uAgent, queryString, ipDetails, country)
            request['httpRequest']['uri'] = finalURLList[x]
            requests.append(copy.deepcopy(request))
    return (requests)

def source_ip_calculate(ipName, country = "", labels = []):
    #print (ipName)
    #print (country)
    #print (labels)
    if ipName == 'user':
        if country == "":
            print ('picking random country')
            country = random.choice(list(ipTable.keys()))
            print (country)
        cidrList = ipTable[country.upper()]
        c = len(cidrList)
        #print ("c: " + str(c))
        if c == 1:
            x = 0
        else:
            x = random.randrange(0,c)
        #print ("x: " + str(x))
        #print (cidrList[x])
        #print (cidrList[x]['Start'])
        #print (cidrList[x]['End'])
        s = int.from_bytes(socket.inet_aton(cidrList[x]['Start']),'big')
        e = int.from_bytes(socket.inet_aton(cidrList[x]['End']),'big')
        ip = socket.inet_ntoa(struct.pack('>I', random.randint(s,e)))
        response = {
                "sourceip": ip,
                "country": country
            }
        if not labels == []:
            response['labels'] = labels
        return (response)

#generate random string, simplified
def random_letters(count=8):
    s = ''.join([random.choice(string.ascii_letters+ string.digits) for n in range(count)])
    return (s)
#Generate a WAF log key path/file name
def waf_file_name(timestamp,region='us-east-1'):
    date_time = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d-%H-%M-%S")
    s3key = datetime.datetime.fromtimestamp(timestamp).strftime("%Y/%m/%d/%H/")
    if not os.path.isdir(s3key):
        print ("Created DIR: " + s3key)
        os.makedirs(s3key)
    filename = (s3key + "-".join(["aws-waf-logs-delivery-fms", region, '1', date_time, random_letters(8), random_letters(4), random_letters(4), random_letters(4), random_letters(12)])).lower()
    return (filename)



output = waf_file_name(startTimeEpoch)
currentHour = datetime.datetime.fromtimestamp(startTimeEpoch).hour
for tzItem in range(1,tzWindowCount):
    #New timestamp
    requestTimeStamp = startTimeEpoch + (tzItem*300)
    print (datetime.datetime.fromtimestamp(requestTimeStamp).strftime("%Y-%m-%d-%H-%M-%S"))
    #Humans using during business hours
    currentHour =  datetime.datetime.fromtimestamp(requestTimeStamp).hour
    if currentHour > 8 and currentHour < 20:
        businessHours = True
    else:
        businessHours = False
    if datetime.datetime.fromtimestamp(requestTimeStamp).isoweekday() in range(1, 6):
        isWeekday = True
    else:
        isWeekday = False
    humansthistz = qrandom(3)*qrandom(3)*qrandom(3)*qrandom(3)
    print ("People this tz: " + str(humansthistz))
    if (businessHours and isWeekday) or (isWeekday == False):
        chance = 0.95
    else:
        chance = .20
    if random.random() < chance:
        for h in range(1,humansthistz):
            requests = simulate_user(
                        requestTimeStamp,
                        args=[],
                        country='US',
                        headers = [],
                        userAgents=['Chrome','Firefox'],
                        method = 'GET',
                        labels=[],
                        ipName='user',
                        initialURLList = ['/'],
                        minInitial = -1,
                        maxInitial = -1,
                        randomURLList= ['/','blue.jpg','/login','/socket.io'],
                        minRandom = qrandom(10),
                        maxrandom = qrandom(30)+10,
                        finalURLList = ["/", "/logout"],
                        minFinal = 1,
                        maxFinal = 2
                    )
            for request in requests:
                try:
                    size = os.fstat(output.fileno()).st_size
                    if size > 50000:
                        output.close()
                        filename = waf_file_name(requestTimeStamp)
                        output = open(filename,'w')
                except:
                    filename = waf_file_name(requestTimeStamp)
                    output = open(filename,'w')
                json.dump(request,output)
    else:
        print ('Nobody this tz')
