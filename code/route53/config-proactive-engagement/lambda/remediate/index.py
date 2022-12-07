import sys
import os
import json
import boto3
import logging
import time

sys.path.insert(0,'./route53/config-proactive-engagement/lambda/remediate')
sys.path.insert(0,'./route53/config-proactive-engagement/lambda/common')

from sqs_tasks import *
from resource_details import *
#from resource_checks import *
from botocore.exceptions import ClientError

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')
accountId = os.environ['AccountId']

snsCalculation = os.environ['SNSCalculation']
codeS3Bucket = os.environ['CodeS3Bucket']
snsTopicDetails = os.environ['snsTopicDetails']
#If there is no value, don't configure a SNSTopicArn
if snsTopicDetails == "":
    snsaccountID = None
    snsTopicName = None
elif snsCalculation == 'LocalAccount':
    snsaccountID = accountId
    snsTopicName = snsTopicDetails
else:
    snsaccountID = snsTopicDetails.split("|")[0]
    snsTopicName = snsTopicDetails.split("|")[1]


shield_client = boto3.client('shield')
ec2_client = boto3.client('ec2')
sqs_client = boto3.client("sqs", region_name=os.environ['AWS_REGION'])

def lambda_handler(protectionId,context):
    logger.debug(protectionId)
    if snsaccountID == None:
        snsTopicArn = "<na>"
    else:
        snsTopicArn = ":".join(["arn:aws:sns",os.environ['AWS_REGION'], snsaccountID, snsTopicName])
    shieldProtectionDetails = get_shield_protection_details(protectionId)
    if 'Error' in shieldProtectionDetails:
        logger.info (shieldProtectionDetails['Error'])
        return ()

    rawResourceArn = shieldProtectionDetails['ResourceArn']
    
    resourceDetails = build_resource_details(rawResourceArn)
    logger.debug("Resource Details")
    logger.debug(resourceDetails)
    resourceArn = resourceDetails['resourceArn']
    resourceId = resourceDetails['resourceId']
    resourceType = resourceDetails['resourceType']
    stackSuffix = resourceDetails['stackSuffix']

    if 'HealthCheckIds' in shieldProtectionDetails:
        healthCheckIds = shieldProtectionDetails['HealthCheckIds']
    else:
        healthCheckIds = []
    logger.debug("ResourceArn: " + resourceArn)
    logger.debug("ResourceId: " + resourceId)
    logger.debug("ResourceType: " + resourceType)
    logger.debug("Stack Suffix: " + stackSuffix)
    logger.debug ("Health Check ID" + json.dumps(healthCheckIds))

    if resourceType == 'cloudfront':
        logger.info ("Found CloudFront")
        response = cloudfront_details(resourceArn.split('/')[1])
    elif resourceType == 'alb':
        logger.info ("Found ALB")
        response = elbv2_details(resourceArn)
    elif resourceType == 'nlb':
        logger.info ("Found NLB")
        response = elbv2_details(resourceArn)
    elif resourceType == 'instance':
        logger.info ("Found EC2 EIP")
        response = ec2_details(resourceArn)
    else:
        logger.info ("Unknown Resource Type")
        return()

    healthCheckS3Key = response['HealthCheckKey']
    templateURL = "https://" + codeS3Bucket + ".s3.amazonaws.com/" + healthCheckS3Key
    defaultProbeFQDN = response['defaultProbeFQDN']
    tags = response['Tags']
    tagkeys = list(tags.keys())

    if 'probeFQDN' in tagkeys:
        probeFQDN = tags['probeFQDN']
    else:
        probeFQDN = defaultProbeFQDN
    if 'probeType' in tagkeys:
        probeType = tags['probeType']
    else:
        probeType = "HTTPS"
    if probeType == "HTTPS":
        enableSNI = True
    else:
        enableSNI = False
    if 'probeSearchString' in tagkeys and probeType in ['HTTP','HTTPS']:
        probeType = probeType + "STRMATCH"
    cfnParameters = [{
                      'ParameterKey': 'resourceArn',
                      'ParameterValue': rawResourceArn
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
                        'ParameterKey': 'resourceId',
                        'ParameterValue': resourceId
                  }
                ]
    listOfTags = [
        'probeSearchString','probeResourcePath','probeType', 'probePort','probeHealthCheckRegions','DDOSSNSTopic',
        'metric1Name','metric1Threshold','metric1Statistic','metric2Name','metric2Threshold','metric2Statistic',
        'metric3Name','metric3Threshold','metric3Statistic'
        ]

    for p in listOfTags:
        if p in tagkeys:
            cfnParameters.append({'ParameterKey': p,'ParameterValue': tags[p]})

    logger.debug("cfnParameters")
    for p in cfnParameters:
        logger.debug(p)

    msg_body = {"action": "Create", "resourceId":resourceId, "stackSuffix": stackSuffix, "templateURL" : templateURL, "cfnParameters" : cfnParameters}

    send_cfn_sqs_message(msg_body)
    