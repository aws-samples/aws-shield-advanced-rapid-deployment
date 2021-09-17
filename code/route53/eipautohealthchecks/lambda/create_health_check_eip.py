import json, boto3, random, os, cfnresponse, time, botocore, logging, uuid, random, string

from delete_health_checks import delete_health_checks
from tag_check import tag_check
from cfn_stack_manage import cfn_stack_manage

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

r53_client = boto3.client('route53')
cw_client = boto3.client('cloudwatch')
ec2_client = boto3.client('ec2')
shield_client = boto3.client('shield')

hc_regions = os.environ['HC_Regions'].split(',')
snsTopicDetails = os.environ['snsTopicDetails']

functionName = os.environ['AWS_LAMBDA_FUNCTION_NAME']

accountId = os.environ['AccountId']
snsaccountID = snsTopicDetails.split("|")[0]
snsTopicName = snsTopicDetails.split("|")[1]
#Construct regional ARN from SNSDetails
snsTopicArn = ":".join(["arn:aws:sns",os.environ['AWS_REGION'],snsaccountID, snsTopicName])

def randStr(chars = string.ascii_uppercase + string.digits, N=10):
	return ''.join(random.choice(chars) for _ in range(N))


def create_health_check_eip(eipAlloc, instanceId):
    eipArn = "arn:aws:ec2:" + os.environ['AWS_REGION'] + ":" + accountId + ":eip-allocation/" + eipAlloc
    cfnTags = []
    try:
      shieldProtection = shield_client.describe_protection(
              ResourceArn=eipArn)
      logger.info(shieldProtection)
    except botocore.exceptions.ClientError as error:
      logger.error(error.response['Error']['Message'])
      if error.response['Error']['Message'] == "The referenced protection does not exist.":
          logger.info("Was not a protected resource, graceful skip")
          return (error.response['Error']['Message'])
    try:
      descAddress = ec2_client.describe_addresses(
            AllocationIds=[eipAlloc])['Addresses'][0]
      networkInterfaceId = descAddress["NetworkInterfaceId"]
      privateIpAddress = descAddress["PrivateIpAddress"]
      cfnTags = [{"Key": "NetworkInterfaceId", "Value": networkInterfaceId}, {"Key": "PrivateIpAddress", "Value": privateIpAddress}]
    except botocore.exceptions.ClientError as error:
      logger.error(error.response['Error']['Message'])
      return (error.response['Error']['Message'])
    logger.debug(eipArn)
    logger.debug(instanceId)
    logger.debug(eipAlloc)
    try:
      ec2Response = ec2_client.describe_instances(
          InstanceIds=[
              instanceId,
          ]
      )['Reservations'][0]['Instances'][0]
      logger.debug("ec2Response")
      logger.debug(ec2Response)
    except botocore.exceptions.ClientError as error:
      logger.debug(error.response['Error']['Message'])
      return (error.response['Error']['Message'])
    if "Tags" in ec2Response:
      ec2_tags = ec2Response['Tags']
    else:
      ec2_tags = []
    tagCheck = tag_check(ec2_tags, True)
    if tagCheck == True:
      logger.info("Tag Match successful")
    else:
      delete_health_checks(eipAlloc)
      logger.info("Tag Match failed, stopping")
      return ("Tag Match failed, stopping")
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
    for tag in ec2_tags:
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

    #Build defaults for probe configuration if tags did not define specific values
    #Connection DNS Name.  Use LB DNS if no custom value provided
    if probeFQDN == None:
      try:
        publicIp = descAddress['PublicIp']
        logger.debug("PublicIP: " + publicIp)
        probeFQDN = "ec2-" + publicIp.replace(".","-") + ".compute-1.amazonaws.com"
      except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error']['Message'])
        raise
    #Connection port/procotol.  If not defined, check if a HTTPS/TCP:443 listener exists, else HTTP/TCP:80, otherwise fail gracefully and build no health checks
    if probePort == None or probeType == None:
      #Get ENI details
      ec2_sGroups = ec2Response['SecurityGroups']
      sgGroupIdList = []
      for sg in ec2_sGroups:
        sgGroupIdList.append(sg['GroupId'])
      sgResponse = ec2_client.describe_security_groups(
        GroupIds=sgGroupIdList)['SecurityGroups']
      sgRuleList = []
      for sg in sgResponse:
        for ipPermission in sg['IpPermissions']:
          for cidr in ipPermission['IpRanges']:
            if cidr['CidrIp'] == "0.0.0.0/0":
              sgRuleList.append({"IpProtocol": ipPermission['IpProtocol'],"Port": ipPermission['ToPort']})
      logger.info("sgRuleList")
      logger.info(sgRuleList)
      if {'IpProtocol': 'tcp', 'Port': 443} in sgRuleList:
        probePort = 443
        probeType = "HTTPS"
        enableSNI = True
      elif {'IpProtocol': 'tcp', 'Port': 80} in sgRuleList:
        probePort = 80
        probeType = "HTTP"
        enableSNI = False
      else:
        logger.info("No defined probeType/port specified or calculated based on Security Group rules, graceful exit")  
        return ()
      if probeSearchString != None and probeType in ['HTTP','HTTPS']:
        probeType = probeType + "STRMATCH"
    cfnParameters = [{
                      'ParameterKey': "InstanceId",
                      'ParameterValue': instanceId
                  },
                  {
                      'ParameterKey': 'probeFQDN',
                      'ParameterValue': probeFQDN
                  },
                  {
                      'ParameterKey': 'SNSTopicNotifications',
                      'ParameterValue': snsTopicArn
                  },
                  {
                      'ParameterKey': "UID",
                      'ParameterValue': randStr()
                  }
                ]
    cfnTags.append({'Key': "FunctionName",'Value': functionName})
    listOfTags = ['probeSearchString','probeResourcePath','probeType',
                  'probePort','probeHealthCheckRegions',
                  'metric1Name','metric1Threshold','metric1Statistic',
                  'metric2Name','metric2Threshold','metric2Statistic']
    for p in listOfTags:
      if not eval(p) == None:
        cfnParameters.append({'ParameterKey': p,'ParameterValue': str(eval(p))})
    networkInterfaceId = descAddress["NetworkInterfaceId"]
    privateIpAddress = descAddress["PrivateIpAddress"]
    stackName = "-".join([eipAlloc,networkInterfaceId,privateIpAddress.replace(".","-")])
    response = cfn_stack_manage(cfnParameters, stackName, [shieldProtection], cfnTags)
    print (response)