import sys
import os
import json
import boto3
import logging
sys.path.insert(0,'./route53/config-proactive-engagement/lambda/remediate')
sys.path.insert(0,'./route53/config-proactive-engagement/lambda/common')
from resource_details import *
from resource_checks import *
from cfn_stack_manage import cfn_stack_manage

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

accountId = os.environ['AccountId']
snsTopicDetails = os.environ['snsTopicDetails']
codeS3Bucket = os.environ['CodeS3Bucket']
snsaccountID = snsTopicDetails.split("|")[0]
snsTopicName = snsTopicDetails.split("|")[1]

shield_client = boto3.client('shield')
ec2_client = boto3.client('ec2')


def lambda_handler(protectionId,context):
    logger.debug(protectionId)
    snsTopicArn = ":".join(["arn:aws:sns",os.environ['AWS_REGION'], snsaccountID, snsTopicName])
    shieldProtectionDetails = identify_resource_type(protectionId)
    resourceType = shieldProtectionDetails['ResourceType']
    if 'HealthCheckIds' in shieldProtectionDetails:
        healthCheckIds = shieldProtectionDetails['HealthCheckIds']
    else:
        healthCheckIds = []
    resourceArn = shieldProtectionDetails['ResourceArn']
    print (resourceArn)
    resourceId = shieldProtectionDetails['ResourceArn'].split('/')[-1]
    '''
    shieldProtectionDetails
    Id: a33aaca6-6e4d-4ace-b7ac-6e8e89ef440d
    Name: FMManagedShieldProtection05752bec-7f2f-48df-9f67-21d4b3ba0ae1
    ResourceArn: arn:aws:cloudfront::470411459345:distribution/ELR8K1QPRMHO0
    HealthCheckIds: []
    ProtectionArn: arn:aws:shield::470411459345:protection/a33aaca6-6e4d-4ace-b7ac-6e8e89ef440d
    ResourceType: cloudfront
    '''

    print ("shieldProtectionDetails")
    for k in list(shieldProtectionDetails.keys()):
        print (k + ": " + str(shieldProtectionDetails[k]))
    print (resourceType)
    print (resourceArn)
    print (healthCheckIds)
    print (resourceId)
    if resourceType == 'cloudfront':
        response = cloudfront_details(resourceArn.split('/')[1])
    elif resourceType == 'alb':
        print ("Found ALB")
        response = elbv2_details(resourceArn)
    elif resourceType == 'nlb':
        print ("Found NLB")
        response = elbv2_details(resourceArn)
    elif resourceType == 'instance':
        print ("Found EC2 EIP")
        response = ec2_details(resourceArn)
    else:
        print ("UNKNOWN RESOURCETYPE")
        return ()
    healthCheckS3Key = response['HealthCheckKey']
    print ("response")
    print (list(response.keys()))
    for k in list(response.keys()):
        print (k + ": " + str(response[k]))

    #return()
    #Update to evaluate if resourceID is a Cloudfront ID
    #response = cloudfront_details(protectionId)
    resourceArn = response['resourceArn']
    defaultProbeFQDN = response['defaultProbeFQDN']
    resoureId = response['resourceId']
    tags = response['Tags']
    tagkeys = list(tags.keys())
    templateURL = "https://" + codeS3Bucket + ".s3.amazonaws.com/" + healthCheckS3Key
    print ("templateURL")
    print (templateURL)
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
    response = cfn_stack_manage(cfnParameters, resoureId, templateURL)
    logger.info(response)
