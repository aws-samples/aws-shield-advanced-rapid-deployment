import boto3
import os
import cfnresponse
import time
import logging
import botocore

from delete_health_checks import delete_health_checks
from cfn_stack_manage import cfn_stack_manage
from tag_check import tag_check

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

elbv2_client = boto3.client('elbv2')
shield_client = boto3.client('shield')

codeS3Bucket = os.environ['CodeS3Bucket']
healthCheckKey = os.environ['HealthCheckKey']
snsTopicDetails = os.environ['snsTopicDetails']
snsaccountID = snsTopicDetails.split("|")[0]
snsTopicName = snsTopicDetails.split("|")[1]

def create_health_check_alb(albArn):
    snsTopicArn = ":".join(["arn:aws:sns",os.environ['AWS_REGION'],snsaccountID, snsTopicName])
    try:
      elb_response = elbv2_client.describe_load_balancers(
            LoadBalancerArns=[
                albArn
              ]
            )
      if elb_response['LoadBalancers'][0]['Scheme'] == 'internal':
        logger.info("internal ALB, graceful skip")
        return()
    except botocore.exceptions.ClientError as error:
      logger.error(error.response['Error']['Message'])
      return (error.response['Error']['Message'])
    #Resource is not a Shield Adv protected resources, do not create Health Checks
    try:
      shieldProtection = shield_client.describe_protection(
              ResourceArn=albArn)
      logger.info(shieldProtection)
    except botocore.exceptions.ClientError as error:
      logger.error(error.response['Error']['Message'])
      if error.response['Error']['Message'] == "The referenced protection does not exist.":
          logger.info("Was not a protected resource, graceful skip")
          return (error.response['Error']['Message'])
    try:
      tags = elbv2_client.describe_tags(
        ResourceArns=[albArn])['TagDescriptions'][0]['Tags']
    except botocore.exceptions.ClientError as error:
      logger.error('There was an issue getting tags for the input resource')
      logger.debug(error.response['Error']['Message'])
      raise
    tagCheck = tag_check(tags, True)
    if tagCheck == True:
      logger.info("Tag Match successful")
    else:
      logger.info("Tags did not match requirements.")
      delete_health_checks(albArn.split('/')[2])
      return ()
    #Check for Probe Configuration Tags
    probeFQDN = None
    probeResourcePath = None
    probeType = None
    probePort = None
    probeHealthCheckRegions = None
    probeSearchString = None
    DDOSSNSTopic = None
    metric1Name = None
    metric1Threshold = None
    metric1Statistic = None
    metric2Name = None
    metric2Threshold = None
    metric2Statistic = None 
    metric3Name = None
    metric3Threshold = None
    metric3Statistic = None

    for tag in tags:
      if tag['Key'] == "ProbeFQDN":
        probeFQDN = tag['Value']
      if tag['Key'] == "ProbeResourcePath":
        probeResourcePath = tag['Value']
      if tag['Key'] == "ProbeType":
        probeType = tag['Value']
      if tag['Key'] == "ProbePort":
        probePort = tag['Value']
      if tag['Key'] == "ProbeSearchString":
        probeSearchString = tag['Value']
      if tag['Key'] == "ProbeHealthCheckRegions":
        probeHealthCheckRegions = tag['Value']
      if tag['Key'] == "DDOSSNSTopic":
        snsTopicArn = tag['Value']  

      if tag['Key'] == "Metric1Name":
        metric1Name = tag['Value']
      if tag['Key'] == "Metric1Statistic":
        metric1Statistic = tag['Value']
      if tag['Key'] == "Metric1Threshold":
        metric1Threshold = tag['Value']

      if tag['Key'] == "Metric2Name":
        metric2Name = tag['Value']
      if tag['Key'] == "Metric2Statistic":
        metric2Statistic = tag['Value']
      if tag['Key'] == "Metric2Threshold":
        metric2Threshold = tag['Value']

      if tag['Key'] == "Metric3Name":
        metric3Name = tag['Value']
      if tag['Key'] == "Metric3Statistic":
        metric3Statistic = tag['Value']
      if tag['Key'] == "Metric3Threshold":
        metric3Threshold = tag['Value']

    #Build defaults for probe configuration if tags did not define specific values
    #ProbeDNS FQDN
    if probeFQDN == None:
      try:
        probeFQDN = elb_response['LoadBalancers'][0]['DNSName']
      except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error']['Message'])
        raise
    #Prove port override if specified and type of probe (http,https or variant with string search)
    if probePort == None and probeType == None:
      try:
        elb_listeners = elbv2_client.describe_listeners(
          LoadBalancerArn=albArn)['Listeners']
      except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error']['Message'])
        raise
      foundHTTPS = False
      #If there is at least on HTTPS listener, only evaluate the port a HTTPS listener
      for listener in elb_listeners:
        if listener['Protocol'] == "HTTPS":
          foundHTTPS = True
          probeType = "HTTPS"
      if probeType == None:
        probeType = "HTTP"
      for listener in elb_listeners:
        if foundHTTPS:
          if listener['Port'] == 443:
            probePort = 443
          elif probePort == None:
            probePort = listener['Port']
        else:
          if listener['Port'] == 80:
            probePort = 80
          elif probePort == None:
            probePort = listener['Port']
    #If probeType was defined but no probePort, look for the best port based on provided probeType
    elif probePort == None and probeType in ['HTTP','HTTPS']:
      try:
        elb_listeners = elbv2_client.describe_listeners(
          LoadBalancerArn=albArn)['Listeners']
      except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error']['Message'])
        raise
      for listener in elb_listeners:
        if probeType == "HTTPS":
          if listener['Port'] == 443:
            probePort = 443
          elif probePort == None:
            probePort = listener['Port']
        else:
          if listener['Port'] == 80:
            probePort = 80
          elif probePort == None:
            probePort = listener['Port']
    else:
      return ("Unable to calculate ProbeType")
    if probeSearchString != None and probeType in ['HTTP','HTTPS']:
      probeType = probeType + "STRMATCH"
    cfnParameters = [{
                      'ParameterKey': 'ALBArn',
                      'ParameterValue': albArn
                  },
                  {
                      'ParameterKey': 'probeFQDN',
                      'ParameterValue': probeFQDN
                  },
                  {
                      'ParameterKey': 'SNSTopicNotifications',
                      'ParameterValue': snsTopicArn
                  }
                ]
    listOfTags = ['probeSearchString','probeResourcePath','probeType',
                  'probePort','probeHealthCheckRegions','DDOSSNSTopic',
                  'metric1Name','metric1Threshold','metric1Statistic',
                  'metric2Name','metric2Threshold','metric2Statistic',
                  'metric3Name','metric3Threshold','metric3Statistic']
    for p in listOfTags:
      if not eval(p) == None:
        cfnParameters.append({'ParameterKey': p,'ParameterValue': str(eval(p))})
    logger.debug("CFNParameters")
    logger.debug(cfnParameters)
    cfn_stack_manage(cfnParameters,albArn.split('/')[2],[shieldProtection])
