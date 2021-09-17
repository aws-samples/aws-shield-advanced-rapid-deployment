import json, boto3, random, os, cfnresponse, time, logging, botocore, uuid, time
from delete_health_checks import delete_health_checks
from tag_check import tag_check
from cfn_stack_manage import cfn_stack_manage

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

r53_client = boto3.client('route53')
cw_client = boto3.client('cloudwatch')
elbv2_client = boto3.client('elbv2')
shield_client = boto3.client('shield')
cfn_client = boto3.client('cloudformation')

CodeS3Bucket = os.environ['CodeS3Bucket']
healthCheckKey = os.environ['HealthCheckKey']
templateURL = "https://" + CodeS3Bucket + ".s3.amazonaws.com/" + healthCheckKey

snsTopicDetails = os.environ['snsTopicDetails']
snsaccountID = snsTopicDetails.split("|")[0]
snsTopicName = snsTopicDetails.split("|")[1]
#Construct regional ARN from SNSDetails
snsTopicArn = ":".join(["arn:aws:sns",os.environ['AWS_REGION'],snsaccountID, snsTopicName])

def create_health_check_nlb(nlbArn,allocationIds = []):
    try:
      elb_response = elbv2_client.describe_load_balancers(
        LoadBalancerArns=[
          nlbArn])
      if elb_response['LoadBalancers'][0]['Scheme'] == 'internal':
        logger.info("internal ALB, graceful skip")
        return()
    except botocore.exceptions.ClientError as error:
      logger.debug(error.response['Error']['Message'])
      raise
    if allocationIds == []:
          #We only can create R53 health checks for customer own EIP's associated to the NLB, if there are none, we will skip gracefully
          allocationIds = []
          for az in elb_response['LoadBalancers'][0]['AvailabilityZones']:
            logger.debug ("AZ Details")
            logger.debug (az)
            if az['LoadBalancerAddresses'] != []:
              if 'AllocationId' in az['LoadBalancerAddresses'][0]:
                allocationIds.append(az['LoadBalancerAddresses'][0]['AllocationId'])
              else:
                print ("No AllocationId")
          if allocationIds == []:
            print ("Exit Gracefully, NLB did not have customer owned EIP's associated to the NLB, these cannot be Shield Protected")
            return ()  
    #Verify Resource is Shield Protected
    accountId = nlbArn.split(":")[4]
    shieldProtections = []
    for allocation in allocationIds:
      logger.debug("allocation")
      logger.debug(allocation)
      try:
        shieldProtections.append(shield_client.describe_protection(
          ResourceArn="arn:aws:ec2:" + os.environ['AWS_REGION'] + ":" + accountId + ":eip-allocation/" + allocation))
      except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error']['Message'])
        if error.response['Error']['Message'] == "The referenced protection does not exist.":
            logger.info("Was not a protected resource, graceful skip")
            return (error.response['Error']['Message'])
        else:
          raise
      logger.debug("shieldProtections")
      logger.debug(shieldProtections)
    try:
      tags = elbv2_client.describe_tags(
        ResourceArns=[nlbArn])['TagDescriptions'][0]['Tags']
    except botocore.exceptions.ClientError as error:
      logger.error('There was an issue getting tags for the input resource')
      logger.debug(error.response['Error']['Message'])
      raise
    tagCheck = tag_check(tags, True)
    if tagCheck == True:
      logger.info("Tag Match successful")
    else:
      delete_health_checks(nlbArn.split('/')[2])
      logger.info("Tags did not match requirements.  Not creating health check for this resource")
      return ()
    #Check for Probe Configuration Tags
    probeFQDN = None
    probeResourcePath = None
    probeType = None
    probePort = None
    probeHealthCheckRegions = None
    probeSearchString = None
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
      if tag['Key'] == "ProbeSearchString":
        probeSearchString = tag['Value']
      if tag['Key'] == "ProbePort":
        probePort = tag['Value']
      if tag['Key'] == "ProbeHealthCheckRegions":
        probeHealthCheckRegions = tag['Value']

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
      probeFQDN = elb_response['LoadBalancers'][0]['DNSName']
    #Prove port override if specified and type of probe (http,https or variant with string search)
    #Identify if we should to TCP or TLS, and on what port
    if probeType == None:
      #Get listeners
      try:
        elb_listeners = elbv2_client.describe_listeners(
          LoadBalancerArn=nlbArn)['Listeners']
      except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error']['Message'])
        raise
      #Default to TCP
      for listener in elb_listeners:
        #Make sure we have at least one listener that response on a TCP port
        if listener['Protocol'] in ["TLS","TCP","TCP_UDP"]:
          probeType = 'TCP'
      #If no TCP listener found abort, either no listener or a UDP listener only exists. Route 53 does not support UDP as a Probe Health Check.
      if probeType == None:
        return()
      if probePort == None:
        for listener in elb_listeners:
          #Check each listener that can respond on TCP
          if listener['Protocol'] in ["TLS","TCP","TCP_UDP"]:
            #If a listener on TCP 443 is possible, we always use this
            if listener['Port'] == 443:
              probePort = 443
            #Unless listener on TCP 443 is possible, default to TCP 80 as secondary option
            elif listener['Port'] == 80 and not probePort == 443:
              probePort = 80
            #IF a listener on TCP any port exists, we use that unless we find a listener on TCP 443 or TCP 80
            elif probePort == None:
              probePort = listener['Port']
      if probeSearchString != None and probeType in ['HTTP','HTTPS']:
        probeType = probeType + "STRMATCH"
    cfnParameters = [{
                      'ParameterKey': 'NLBArn',
                      'ParameterValue': nlbArn
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
    cfn_stack_manage(cfnParameters,nlbArn.split('/')[2],shieldProtections)
