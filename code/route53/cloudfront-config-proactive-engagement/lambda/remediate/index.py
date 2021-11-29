import sys
sys.path.insert(0,'./route53/cloudfront-config-proactive-engagement/lambda/remediate')
import os
import json
import boto3
import logging
from resource_details import *
from cfn_stack_manage import cfn_stack_manage

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

accountId = os.environ['AccountId']
snsTopicDetails = os.environ['snsTopicDetails']
codeS3Bucket = os.environ['CodeS3Bucket']
snsaccountID = snsTopicDetails.split("|")[0]
snsTopicName = snsTopicDetails.split("|")[1]
def lambda_handler(protectionId,context):
    logger.debug(protectionId)
    snsTopicArn = ":".join(["arn:aws:sns",os.environ['AWS_REGION'], snsaccountID, snsTopicName])
    #Update to evaluate if resourceID is a Cloudfront ID
    response = cloudfront_details(protectionId)
    resourceArn = response['resourceArn']
    defaultProbeFQDN = response['defaultProbeFQDN']
    shieldProtection = response['ShieldProtection']
    resoureId = response['ResourceId']
    tags = response['Tags']
    tagkeys = list(tags.keys())
    healthCheckS3Key = response['HealthCheckKey']
    templateURL = "https://" + codeS3Bucket + ".s3.amazonaws.com/" + healthCheckS3Key
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
                      'ParameterValue': resourceArn
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
    listOfTags = ['probeSearchString','probeResourcePath','probeType', 'probePort','probeHealthCheckRegions','DDOSSNSTopic',
                  'metric1Name','metric1Threshold','metric1Statistic','metric2Name','metric2Threshold','metric2Statistic',
                  'metric3Name','metric3Threshold','metric3Statistic'
                  ]
    for p in listOfTags:
      if p in locals():
        cfnParameters.append({'ParameterKey': p,'ParameterValue': str(eval(p))})
    response = cfn_stack_manage(cfnParameters,resoureId,[shieldProtection],healthCheckS3Key)
    logger.info(response)
