import json, boto3, random, os, cfnresponse, time, botocore, logging, uuid
from delete_health_checks import delete_health_checks
from cfn_stack_manage import cfn_stack_manage
from tag_check import tag_check

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

cf_client = boto3.client('cloudfront')
shield_client = boto3.client('shield')

accountId = os.environ['AccountId']
snsTopicDetails = os.environ['snsTopicDetails']
codeS3Bucket = os.environ['CodeS3Bucket']
healthCheckKey = os.environ['HealthCheckKey']
templateURL = "https://" + codeS3Bucket + ".s3.amazonaws.com/" + healthCheckKey
snsaccountID = snsTopicDetails.split("|")[0]
snsTopicName = snsTopicDetails.split("|")[1]
#Construct regional ARN from SNSDetails
def create_health_check_cf(cfId):
    snsTopicArn = ":".join(["arn:aws:sns",os.environ['AWS_REGION'], snsaccountID, snsTopicName])
    logger.debug(cfId)
    cfArn = "arn:aws:cloudfront::" + accountId + ":distribution/" + cfId
    logging.debug(cfArn)
    try:
      shieldProtection = shield_client.describe_protection(
              ResourceArn=cfArn)
    except botocore.exceptions.ClientError as error:
        logger.info(error.response['Error']['Message'])
        if error.response['Error']['Message'] == "The referenced protection does not exist.":
            logger.info("Was not a protected resource, graceful skip")
            return (error.response['Error'])
    #Validate Tags if configured
    try:
      tags = cf_client.list_tags_for_resource(
        Resource=cfArn)['Tags']['Items']
    except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error'])
        return()
    tagCheck = tag_check(tags, True)
    if tagCheck == True:
      logger.info("Tag Match successful")
    else:
      delete_health_checks(cfId)
      logger.info("Tags did not match requirements.")
      return ()
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
    try:
      getDistro = cf_client.get_distribution(
        Id=cfId)
    except botocore.exceptions.ClientError as error:
      logger.debug(error.response['Error'])
      return ("Error getting tags")
    #Connection DNS Name.  Use LB DNS if no custom value provided
    if probeFQDN == None:
      probeFQDN = getDistro['Distribution']['DomainName']
    #Connection port/procotol.  If not defined, check if a HTTPS/TCP:443 listener exists, else HTTP/TCP:80, otherwise fail gracefully and build no health checks
    if probeType == None:
      probeType = "HTTPS"
    if probeType == "HTTPS":
      enableSNI = True
    else:
      enableSNI = False
    if probeSearchString != None and probeType in ['HTTP','HTTPS']:
      probeType = probeType + "STRMATCH"
    cfnParameters = [{
                      'ParameterKey': 'CFArn',
                      'ParameterValue': cfArn
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
    response = cfn_stack_manage(cfnParameters,cfId,[shieldProtection])
    logger.info(response)