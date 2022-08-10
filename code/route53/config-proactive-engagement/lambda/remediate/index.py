import sys
import os
import json
import boto3
import logging
import time

sys.path.insert(0,'./route53/config-proactive-engagement/lambda/remediate')
sys.path.insert(0,'./route53/config-proactive-engagement/lambda/common')
from resource_details import *
from resource_checks import *
# from cfn_stack_manage import cfn_stack_manage
from botocore.exceptions import ClientError

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

accountId = os.environ['AccountId']
snsTopicDetails = os.environ['snsTopicDetails']
codeS3Bucket = os.environ['CodeS3Bucket']
snsaccountID = snsTopicDetails.split("|")[0]
snsTopicName = snsTopicDetails.split("|")[1]


shield_client = boto3.client('shield')
ec2_client = boto3.client('ec2')
sqs_client = boto3.client("sqs", region_name=os.environ['AWS_REGION'])

def lambda_handler(protectionId,context):
    instaceId4Ec2 = "<na>"
    logger.debug(protectionId)
    snsTopicArn = ":".join(["arn:aws:sns",os.environ['AWS_REGION'], snsaccountID, snsTopicName])
    shieldProtectionDetails = identify_resource_type(protectionId,[])
    resourceType = shieldProtectionDetails['ResourceType']
    print("--------------------------------------")
    print(resourceType)
    print("--------------------------------------")
    if 'HealthCheckIds' in shieldProtectionDetails:
        healthCheckIds = shieldProtectionDetails['HealthCheckIds']
    else:
        healthCheckIds = []
    resourceArn = shieldProtectionDetails['ResourceArn']
    print("start")
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
        instaceId4Ec2 = response.get('resourceArn').split('/',maxsplit=1)[1]
        print(instaceId4Ec2)
    elif resourceType == 'instance':
        print ("Found EC2 EIP")
        response = ec2_details(resourceArn)
        instanceId = getEc2InstanceId(shieldProtectionDetails['ResourceArn'],shieldProtectionDetails['ResourceType'])
        instaceId4Ec2Describe = ec2_client.describe_addresses( Filters=[{'Name': 'allocation-id','Values': [instanceId] }])
        instaceId4Ec2 = instaceId4Ec2Describe.get('Addresses')[0].get('InstanceId')
        print(instaceId4Ec2)
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
    print(f'The current value for resourceID is ------------->{instaceId4Ec2}<------------------')
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
                  },
                  {
                        'ParameterKey': 'resourceId',
                        'ParameterValue': instaceId4Ec2
                  }
                ]
    listOfTags = ['probeSearchString','probeResourcePath','probeType', 'probePort','probeHealthCheckRegions','DDOSSNSTopic',
                  'metric1Name','metric1Threshold','metric1Statistic','metric2Name','metric2Threshold','metric2Statistic',
                  'metric3Name','metric3Threshold','metric3Statistic'
                  ]
    for p in listOfTags:
        if p in locals():
            cfnParameters.append({'ParameterKey': p,'ParameterValue': str(eval(p))})
    
    #######################  SEND resoureId, templateURL and cfnParameters TO SQS QUEUE  ##############################        
    print('###########')
    msg_body = {"resoureId": resoureId, "templateURL" : templateURL, "cfnParameters" : cfnParameters}
    
    try:
        if len(healthCheckIds) == 0:

            response = sqs_client.send_message(QueueUrl=os.environ['SQS_QUEUE_URL'],
                                            MessageBody=json.dumps(msg_body))
            logger.debug("message_sent")
            logger.info(response)
        else:
            logger.info(f"HealthCheckIDs {healthCheckIds} is associated with the resource:: {resoureId}")
    except ClientError:
        logger.exception(f'Could not send meessage')
        raise
    else:
        return response
    
    ################################################
    # response = cfn_stack_manage(cfnParameters, resoureId, templateURL)
    # print(f'This is the response for CfnParameters, ResourceID and TemplateURL: {response}')
    # print("Delay Starts")
    # time.sleep(63)
    # print("Delay Ends")
    # logger.info(response)