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
import faker
fakeStuff = faker.Faker()
botAttack = 0
hostvalue = 'd2tnwzehnrl3ke.cloudfront.net'
monitorbots = [{
            "sourceip": "15.177.34.92",
            "country": "IE",
            "labels": []
        },{
            "sourceip": "15.177.38.92",
            "country": "IE",
            "labels": []
        },{
            "sourceip": "15.177.6.92",
            "country": "US",
            "labels": []
        },{
            "sourceip": "15.177.2.94",
            "country": "IE",
            "labels": []
        },{
            "sourceip": "15.177.18.92",
            "country": "IE",
            "labels": []
        },{
            "sourceip": "15.177.22.92",
            "country": "IE",
            "labels": []
        }]
monitoringHeaders = [
    {
        "name": "Connection", "value": "close"
    },
    {
        "name": "Accept","value": "*/*"
    }
]

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

with open('user_request_components.json') as h:
    userRequestComponents = json.loads(h.read())

userInitialList = userRequestComponents['Landing']
userRandomList = userRequestComponents['Images']
userRandomList += userRequestComponents['Review']
userRandomList += userRequestComponents['Cart']
userFinalList = userRequestComponents['Checkout']

rootURL = "http://dcqqtulaepd1q.cloudfront.net/"
request = copy.deepcopy(requestTemplate)

#actual data
#November 9, 2021 8:00:00 PM GMT-05:00
#startTimeEpoch = 1636506000
#November 28, 2021 8:00:00 PM GMT-05:00
#endTimeEpoch = 1638147600

#shorter test range
#August 31, 2021 9:00:00 PM GMT-04:00
startTimeEpoch = 1630458000
#Wednesday, September 1, 2021 1:00:00 AM
endTimeEpoch = 1635790615
tzWindowCount = math.floor((endTimeEpoch - startTimeEpoch)/300)
##print (tzWindowCount)
def gen_request_id():
    return (''.join([random.choice(string.ascii_letters+ string.digits) for n in range(32)]) + '==')
#botCountries  = ["ZZ", "AU", "CN", "JP","TH","IN","MY","KR","SG","HK","US","TW","KH","PH","VN","FR","ES","GB","CZ","DE","AT",
#                    "CH","BR","IT","NL","GR","IE","DK","PT","SE","GH","RU","CM","ZA","TR","AE","PL","JO","BE","RO","AR",
#                    "UG","AM","TZ","BI","UY","NO","CL","LU","FI","BG","UA","EG","CA","IL","QA","MD","IQ","LV","UZ","SK","KZ",
#                    "GE","EE","HR","US","US","US","US"]
botCountries = ["US","DE"]
def user_agent_header(userAgent,headers):
    found = False
    for header in headers:
        if header['name'] == 'User-Agent':
            header['value'] == userAgent
    if found == False:
        headers.append(
            {
                'name': 'User-Agent',
                'value': userAgent
            }
        )
    return (headers)
def write_to_log(requests, output):
    if requests == []:
        return (output)
    try:
        output
    except:
        ##print ('initial open file')
        filename = waf_file_name(requestTimeStamp)
        output = open(filename,'w')

    else:
        for request in requests:
            try:
                size = os.fstat(output.fileno()).st_size
            except:
                filename = waf_file_name(requestTimeStamp)
                output = open(filename,'w')
                size = 0
            if size > 5000000:
                ##print ("new file time")
                output.close()
                filename = waf_file_name(requestTimeStamp)
                output = open(filename,'w')
            output.write(json.dumps(request))
            output.write('\n')
    return (output)
def generate_rule_match_data(headers, userAgent, args, ipDetails):
    response = {
        "labels": [],
        "ntRules": []
    }
    labelList = []
    for l in ipDetails['labels']:
        labelList.append(l['name'])
    #print ("Initial Response")
    #print (response)
    #No User Agent
    if userAgent == "":
        labelList.append('awswaf:managed:aws:core-rule-set:NoUserAgent_Header')
        response['ntRules'].append({"ruleId" :'AWS-AWSManagedRulesCommonRuleSet','action': 'COUNT'})
    #Social Media caterogy, name and ntrule
    if 'facebook' in userAgent.lower():
        labelList.append('awswaf:managed:aws:bot-control:bot:name:facebook')
        labelList.append('awswaf:managed:aws:bot-control:bot:category:social_media')
        response['ntRules'].append({"ruleId" :'AWS-AWSManagedRulesBotControlRuleSet','action': 'COUNT'})
    elif 'twitter' in userAgent.lower():
        labelList.append('awswaf:managed:aws:bot-control:bot:name:twitter')
        labelList.append('awswaf:managed:aws:bot-control:bot:category:social_media')
        response['ntRules'].append({"ruleId" :'AWS-AWSManagedRulesBotControlRuleSet','action': 'COUNT'})
    elif 'linkedin' in userAgent.lower():
        labelList.append('awswaf:managed:aws:bot-control:bot:name:linkedin')
        labelList.append('awswaf:managed:aws:bot-control:bot:category:social_media')
        response['ntRules'].append({"ruleId" :'AWS-AWSManagedRulesBotControlRuleSet','action': 'COUNT'})
    #Matching rules from ipDetails labels
    for l in response['labels']:
        if 'anonymous-ip' in labelList:
            response['ntRules'].append({'ruleId':'AWS-AWSManagedRulesAnonymousIpList'})
    for l in list(set(labelList)):
        response['labels'].append({'name': l})
    return (response)

def fake_request(requestTimeStamp, method, headers, userAgent, args, ipDetails, ntRules = []):
    fakeRequest = copy.deepcopy(requestTemplate)
    fakeRequest['nonTerminatingMatchingRules'] = ntRules
    ruleMatchData = copy.deepcopy(generate_rule_match_data(headers, userAgent, args, ipDetails))
    #print ("ruleMatchData")
    #print (ruleMatchData)
    fakeRequest['labels'] = ruleMatchData['labels']
    fakeRequest['nonTerminatingMatchingRules'] = ruleMatchData['ntRules']
    httpRequest = fakeRequest['httpRequest']
    httpRequest['requestId'] = gen_request_id()
    fakeRequest['timestamp'] = requestTimeStamp * 1000
    httpRequest['httpMethod'] = method
    httpRequest['args'] = args
    httpRequest['headers'] = user_agent_header(userAgent, headers)
    httpRequest['clientIp'] = ipDetails['sourceip']
    httpRequest['country'] = ipDetails['country']
    if 'labels' in ipDetails:
        fakeRequest['labels'] = copy.deepcopy( ipDetails['labels'])
    return (copy.deepcopy(fakeRequest))

def simulate_user(requestTimeStamp, args, country, headers = [], userAgents=[], method = 'GET', labels=[], ipName = 'user', initialURLList = [], minInitial = -1, maxInitial = -1, randomURLList= [], minRandom = 0, maxRandom = 0,finalURLList = [], minFinal = -1, maxFinal = -1):
    #print ('start simulate')
    #print (labels)
    #print (ipName)
    requests = []
    ntrules = []
    l = len(initialURLList)
    if userAgents == []:
        uAgent = ""
    else:
        uAgent = random.choice(userAgents)
    if not args == []:
        queryString = random.choice(args)
    else:
        queryString = ""
    ipDetails = source_ip_calculate(ipName, country, labels)
    if minInitial == -1:
        minInitial = l
        maxInitial = l
    if maxInitial == -1:
        maxInitial = l

    if maxInitial > l:
        maxInitial = l
    if minInitial > l:
        minInitial = l
    if not minInitial == maxInitial:
        y = random.randrange(minInitial,maxInitial)
    else:
        y = maxInitial
    #Make the initial Requests
    ##print ("###################################################################################################################")
    ##print ("###################################################################################################################")
    ##print ("###################################################################################################################")
    ##print ("User | Initial | Requests: " + str(y))
    ##print ("IP is: " + ipDetails['sourceip'])
    if not initialURLList == []:
        for x in range(0,y):
            #Go the general stuff
            request = fake_request(requestTimeStamp, method, headers, uAgent, queryString, ipDetails, ntrules)
            request['httpRequest']['uri'] = initialURLList[x]
            ##print (request['httpRequest']['uri'])
            ##print (request['httpRequest']['requestId'])
            ##print (request)
            requests.append(copy.deepcopy(request))
        #Make middle random requests
    if minRandom >= maxRandom:
        y = maxRandom
    else:
        y = random.randrange(minRandom,maxRandom)
    ##print ("User | Random | Requests: " + str(y))
    ##print (randomURLList)
    if not randomURLList == []:
        for x in range(0,y):
            #Go the general stuff
            request = fake_request(requestTimeStamp, method, headers, uAgent, queryString, ipDetails, ntrules)
            request['httpRequest']['uri'] = random.choice(randomURLList)
            ##print (request['httpRequest']['uri'])
            ##print (request['httpRequest']['requestId'])
            requests.append(copy.deepcopy(request))
    #Make final Requests
    ##print ("User | Final | Requests: " + str(y))
    if not minFinal == maxFinal:
        y = random.randrange(minFinal,maxFinal)
    else:
        y = maxFinal
    if not finalURLList == []:
        for x in range(0,y):
            #Go the general stuff
            request = fake_request(requestTimeStamp, method, headers, uAgent, queryString, ipDetails, ntrules)
            request['httpRequest']['uri'] = finalURLList[x]
            ##print (request['httpRequest']['uri'])
            ##print (request['httpRequest']['requestId'])
            requests.append(copy.deepcopy(request))
    return (requests)
def decide_headers(name):
    headers = []
    headers.append({
        "name":"Host",
        "value": hostvalue
        }
    )
    if name == 'badbot':
        headers.append(
            {
                "name":"BadStuff",
                "value": "DIE"
                }
            )
    return (headers)
def source_ip_calculate(ipName, country = "", labels = []):
    #print ("SIC")
    #print (ipName)
    #print (country)
    #print (labels)
    if country == "":
        ##print ('picking random country')
        country = random.choice(list(ipTable.keys()))
        ##print (country)
    if ipName == 'user':
        cidrList = ipTable[country.upper()]
        c = len(cidrList)
        ##print ("c: " + str(c))
        if c == 1:
            x = 0
        else:
            x = random.randrange(0,c)
        ##print ("x: " + str(x))
        ##print (cidrList[x])
        ##print (cidrList[x]['Start'])
        ##print (cidrList[x]['End'])
        s = int.from_bytes(socket.inet_aton(cidrList[x]['Start']),'big')
        e = int.from_bytes(socket.inet_aton(cidrList[x]['End']),'big')
        ip = socket.inet_ntoa(struct.pack('>I', random.randint(s,e)))
        response = {
                "sourceip": ip,
                "country": country
            }
        response['labels'] = labels
        return (response)
    elif ipName == 'anonymousBadBot':
        cidrList = badBotCIDRRanges[country]
        c = len(cidrList)
        if c == 1:
            x = 0
        else:
            x = random.randrange(0,c)
        ##print ("x: " + str(x))
        ##print (cidrList[x])
        ##print (cidrList[x]['Start'])
        ##print (cidrList[x]['End'])
        s = int.from_bytes(socket.inet_aton(cidrList[x]['Start']),'big')
        e = int.from_bytes(socket.inet_aton(cidrList[x]['End']),'big')
        ip = socket.inet_ntoa(struct.pack('>I', random.randint(s,e)))
        response = {
                "sourceip": ip,
                "country": country
            }
        response['labels'] = labels
        response['labels'].append({'name':'awswaf:managed:aws:anonymous-ip-list:HostingProviderIPList'})
        return (response)
    elif ipName == 'knownbotdatacenter':
        cidrList = badBotCIDRRanges[country]
        c = len(cidrList)
        if c == 1:
            x = 0
        else:
            x = random.randrange(0,c)
        ##print ("x: " + str(x))
        ##print (cidrList[x])
        ##print (cidrList[x]['Start'])
        ##print (cidrList[x]['End'])
        s = int.from_bytes(socket.inet_aton(cidrList[x]['Start']),'big')
        e = int.from_bytes(socket.inet_aton(cidrList[x]['End']),'big')
        ip = socket.inet_ntoa(struct.pack('>I', random.randint(s,e)))
        response = {
                "sourceip": ip,
                "country": country
            }
        response['labels'] = labels
        return (response)
    elif ipName == 'okBot':
        cidrList = okBotCIDRRanges[country]
        c = len(cidrList)
        if c == 1:
            x = 0
        else:
            x = random.randrange(0,c)
        ##print ("x: " + str(x))
        ##print (cidrList[x])
        ##print (cidrList[x]['Start'])
        ##print (cidrList[x]['End'])
        s = int.from_bytes(socket.inet_aton(cidrList[x]['Start']),'big')
        e = int.from_bytes(socket.inet_aton(cidrList[x]['End']),'big')
        ip = socket.inet_ntoa(struct.pack('>I', random.randint(s,e)))
        response = {
                "sourceip": ip,
                "country": country
            }
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
        ##print ("Created DIR: " + s3key)
        os.makedirs(s3key)
    filename = (s3key + "-".join(["aws-waf-logs-delivery-fms", region, '1', date_time, random_letters(8), random_letters(4), random_letters(4), random_letters(4), random_letters(12)])).lower()
    return (filename)


#Establish list of coutries for knownbotdatacenter source CIDR ranges

badBotCIDRRanges = {}
for country in botCountries:
    cidrList = ipTable[country]
    c = len(cidrList)
    if c <= 1:
        x = 0
    else:
        x = random.randrange(0,c)
    ##print ("cidrList")
    ##print (cidrList)
    ##print ("x: " + str(x))
    ##print (cidrList[x])
    #Claim this as a bad bot only ranges
    if country in badBotCIDRRanges:
        badBotCIDRRanges[country].append(copy.deepcopy(cidrList[x]))
    else:
        ##print (cidrList[x])
        badBotCIDRRanges[country] = [copy.deepcopy(cidrList[x])]

    #Delete from the cidr list otherwise
    cidrList.pop(x)
    ##print ("FIN")
okBotCIDRRanges = {}
for country in botCountries:
    cidrList = ipTable[country]
    c = len(cidrList)
    ##print ("c: " + str(c))
    if c == 1:
        x = 0
    else:
        x = random.randrange(0,c)
    ##print ("cidrList")
    ##print (cidrList)
    ##print ("x: " + str(x))
    ##print (cidrList[x])

    #Claim this as ok bot ranges
    if country in okBotCIDRRanges:
        okBotCIDRRanges[country].append(copy.deepcopy(cidrList[x]))
    else:
        okBotCIDRRanges[country] = [copy.deepcopy(cidrList[x])]
    #Delete from the cidr list otherwise
    cidrList.pop(x)


output = waf_file_name(startTimeEpoch)
currentHour = datetime.datetime.fromtimestamp(startTimeEpoch).hour
for tzItem in range(1,tzWindowCount):
    #New timestamp
    requestTimeStamp = startTimeEpoch + (tzItem*300)
    #Humans using during business hours
    currentHour =  datetime.datetime.fromtimestamp(requestTimeStamp).hour
    currentDay = datetime.datetime.fromtimestamp(requestTimeStamp).day
    if currentHour > 8 and currentHour < 20:
        businessHours = True
    else:
        businessHours = False
    if datetime.datetime.fromtimestamp(requestTimeStamp).isoweekday() in range(1, 6):
        isWeekday = True
    else:
        isWeekday = False
    ##print ("Business Hours: " + str(businessHours))
    ##print ("IsWeekDay: " + str(isWeekday))
    #Humans during business hours and all weekend
    if (businessHours and isWeekday) or (isWeekday == False):
        chance = 0.95
        humansThistz = qrandom(3)*qrandom(3)*qrandom(3)*qrandom(3)
    else:
        chance = .20
        humansThistz = qrandom(5)
    print (datetime.datetime.fromtimestamp(requestTimeStamp).strftime("%Y-%m-%d-%H-%M-%S"))
    if isWeekday:
        print ("It is a weekday")
    else:
        print ("It is a weekend")
    if businessHours:
        print ("It is business hours")
    else:
        print ("It is NOT business hours")
    requests = []
    if random.random() < chance:
        print (str(humansThistz) + " unique humans this TZ")
        for h in range(1,humansThistz):
            request = simulate_user(
                        requestTimeStamp,
                        args=[],
                        country='US',
                        headers = [],
                        userAgents=[fakeStuff.firefox(),fakeStuff.opera(),fakeStuff.chrome(),fakeStuff.firefox(),fakeStuff.opera(),fakeStuff.chrome(),fakeStuff.user_agent()],
                        method = 'GET',
                        labels=[],
                        ipName='user',
                        initialURLList = userInitialList,
                        minInitial = -1,
                        maxInitial = -1,
                        randomURLList= userRandomList,
                        minRandom = qrandom(10),
                        maxRandom = (qrandom(20)*qrandom(10))+10,
                        finalURLList = userFinalList,
                        minFinal = 1,
                        maxFinal = 18
                    )
            for r in request:
                requests.append(copy.deepcopy(r))
            ##print ("Request Records: " + str(len(requests)))
        output = write_to_log(requests, output)
    #############################################################################
    #############################################################################
    #############################################################################
    #Social Media bot traffic
    socialMediaThisTZ = qrandom(4)* qrandom(5)
    print (str(socialMediaThisTZ) + " unique Social media bots this TZ")
    for h in range(1,socialMediaThisTZ):
        request = simulate_user(
                    requestTimeStamp,
                    args=[],
                    country='US',
                    headers = [],
                    userAgents=[
                        'facebookexternalhit',
                        'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)',
                        'Twitterbot/1.0',
                        'Twitterbot',
                        'LinkedInBot/1.0 (compatible; Mozilla/5.0; Jakarta Commons-HttpClient/3.1 +http://www.linkedin.com)',
                        'LinkedInBot/1.0 (compatible; Mozilla/5.0; Jakarta Commons-HttpClient/3.1 +http://www.linkedin.com)',
                        ],
                    method = 'GET',
                    labels=[],
                    ipName='okBot',
                    initialURLList = ["/","/robot.txt"],
                    minInitial = 1,
                    maxInitial = 2,
                    randomURLList= userRandomList,
                    minRandom = qrandom(10),
                    maxRandom = (qrandom(10)*qrandom(10))+10,
                    finalURLList = [],
                    minFinal = -1,
                    maxFinal = -1
                )
        for r in request:
            requests.append(copy.deepcopy(r))
        ##print ("Request Records: " + str(len(requests)))
    output = write_to_log(requests, output)

    #############################################################################
    #############################################################################
    #############################################################################
    #Known bot data centers being bad
    #If an attack is not in progress
    requests = []
    attackChance = 0.05
    if botAttack == 0:
        #Check ones a day if tehre is a bot attack
        if currentDay == datetime.datetime.fromtimestamp(requestTimeStamp).day:
            if random.random() < attackChance:
                print ("Bot Attack Chance rolled!")
                #10 - 20 periods in length
                botAttack = (random.random() * 10) + 10
                botSources = []
                for x in range(1,(qrandom(2)+5)):
                    ##print (x)
                    labels = [
                        {'name':'awswaf:managed:aws:bot-control:signal:KnownBotDataCenter'}
                    ]
                    ipDetails = copy.deepcopy(source_ip_calculate('knownbotdatacenter', random.choice(botCountries), labels))
                    ##print ("ipDetails: ")
                    ##print (ipDetails)
                    botsource = {}
                    botsource['ipDetails'] = copy.deepcopy(ipDetails)
                    botsource['uAgent'] = copy.deepcopy(random.choice([fakeStuff.user_agent(),"","","",""]))
                    botsource['ntrules'] =[]
                    botSources.append(copy.deepcopy(botsource))
                ##print ("botSources")
                ##print (botSources)
        else:
            currentDay = datetime.datetime.fromtimestamp(requestTimeStamp)
    if botAttack >= 1:
        print ("Bot Attack continues: " + (datetime.datetime.fromtimestamp(requestTimeStamp).strftime("%Y-%m-%d-%H-%M-%S")))
        botAttack = botAttack - 1
        for botsource in botSources:
            requestcount = (qrandom(100)*qrandom(10))+2000
            for x in range(1,requestcount):
                request = fake_request(requestTimeStamp, 'GET', decide_headers('badbot'), botsource['uAgent'], "", botsource['ipDetails'], [])
                request['httpRequest']['uri'] = random.choice([
                            fakeStuff.uri_path(),
                            fakeStuff.uri_page(),
                            "/".join([fakeStuff.uri_page(),fakeStuff.domain_word() + fakeStuff.uri_extension()]),
                            "/".join([fakeStuff.uri_path(),fakeStuff.domain_word() + fakeStuff.uri_extension()])
                            ])
                requests.append(copy.deepcopy(request))
        output = write_to_log(requests, output)

    #############################################################################
    #############################################################################
    #############################################################################
    #Route 53 Monitoring
    requests = []
    userAgent = "Amazon-Route53-Health-Check-Service (ref 11111111-11111-1111-11111-1111111111 report http://amzn.to/1vsZADi)"
    for mbot in monitorbots:
        for x in range(1,10):
            ##print (x)
            request = fake_request(requestTimeStamp, 'GET', monitoringHeaders, userAgent, "", mbot, [])
            request['httpRequest']['uri'] = "/"
            requests.append(copy.deepcopy(request))
    output = write_to_log(requests, output)
    #############################################################################
    #############################################################################
    #############################################################################
    #Anonymous good and bad requests
    #Random bad bots
    requests = []
    if random.random() < 0.85:
        requestcount = (qrandom(15)*qrandom(10))+100
        userAgent = random.choice([fakeStuff.firefox(),fakeStuff.opera(),fakeStuff.chrome(),fakeStuff.firefox(),fakeStuff.opera(),fakeStuff.chrome(),fakeStuff.user_agent(), ""])
        for x in range(1,requestcount):
            ##print (x)
            request = fake_request(requestTimeStamp, 'GET', decide_headers('badbot'), userAgent, "", source_ip_calculate('anonymousBadBot'), [])
            request['httpRequest']['uri'] = random.choice([
                        fakeStuff.uri_path(),
                        fakeStuff.uri_page(),
                        "/".join([fakeStuff.uri_page(),fakeStuff.domain_word() + fakeStuff.uri_extension()]),
                        "/".join([fakeStuff.uri_path(),fakeStuff.domain_word() + fakeStuff.uri_extension()])
                        ])
            requests.append(copy.deepcopy(request))

    ##print ("writing to file(s)")
    output = write_to_log(requests, output)
    #High chance of 1 or 2 anonymous humans
    if random.random() < 0.90:
        humansThistz = qrandom(2)
        for h in range(1,humansThistz):
            request = simulate_user(
                        requestTimeStamp,
                        args=[],
                        country='US',
                        headers = [],
                        userAgents=[fakeStuff.firefox(),fakeStuff.opera(),fakeStuff.chrome(),fakeStuff.firefox(),fakeStuff.opera(),fakeStuff.chrome(),fakeStuff.user_agent()],
                        method = 'GET',
                        labels=[{'name':'awswaf:managed:aws:anonymous-ip-list:HostingProviderIPList'}],
                        ipName='user',
                        initialURLList = userInitialList,
                        minInitial = -1,
                        maxInitial = -1,
                        randomURLList= userRandomList,
                        minRandom = qrandom(10),
                        maxRandom = (qrandom(20)*qrandom(10))+10,
                        finalURLList = userFinalList,
                        minFinal = 1,
                        maxFinal = 18
                    )
            for r in request:
                requests.append(copy.deepcopy(r))
            ##print ("Request Records: " + str(len(requests)))
        output = write_to_log(requests, output)
#aws s3 sync ./2021/ s3://central-waf-logs-225449158849-us-east-1/firehose/us-east-1/2021/ --delete
