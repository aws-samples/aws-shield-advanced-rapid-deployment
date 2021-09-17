import sys
sys.path.insert(0,'./route53/lambda/cloudfrontHC')
import json
import boto3
import random
import os
import cfnresponse
import time
import logging
import botocore
from create_health_check_cf import create_health_check_cf
from delete_health_checks import delete_health_checks

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

cf_client = boto3.client('cloudfront')
shield_client = boto3.client('shield')
sqs_client = boto3.client('sqs')

accountId = os.environ['AccountId']
sqsQueueURL = os.environ['sqsQueueURL']

def lambda_handler(event, context):
    logger.debug(event)
    responseData = {}
    #If a call from a custom lambda backed resource
    if 'RequestType' in event:
        if (event['RequestType'] == 'Create' or event['RequestType'] == 'Update'):
            cfDistros = cf_client.list_distributions()
            if 'Items' in cfDistros['DistributionList']:
                for distro in cfDistros['DistributionList']['Items']:
                    try:
                        logger.info("Created synthetic create message so we try again later but CFN can finish")
                        message = {
                            "account": accountId,
                            "detail": {
                                "eventName": "CreateDistribution",
                                "responseElements": {
                                        "distribution": {
                                            "id": distro['Id']
                                            }
                                        }
                                    }
                                }
                        response = sqs_client.send_message(
                            QueueUrl=sqsQueueURL,
                            MessageBody=json.dumps(message),
                            DelaySeconds=5
                            )
                        logger.debug(response)
                    except botocore.exceptions.ClientError as error:
                        logger.error(error.response['Error'])
                        cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SQSSyntheticEventFailed")
                        return()
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "SQSSyntheticEventSucceeded")
        elif event['RequestType'] == 'Delete':
            try:
                cfDistros = cf_client.list_distributions()
                if 'Items' in cfDistros['DistributionList']:
                    for distro in cfDistros['DistributionList']['Items']:
                        delete_health_checks(distro['Id'])
                cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CFNDeleteSuccessful")
            except botocore.exceptions.ClientError as error:
                logger.error(error.response['Error'])
                responseData['Error'] = error.response['Error']
                cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "CFNDeleteFailed")
                return()
    elif 'Records' in event:
        for record in event['Records']:
            recordEvent = json.loads(record['body'])
            logger.debug(recordEvent)
            logger.info(recordEvent['detail']['eventName'])
            #Creating Create
            if recordEvent['detail']['eventName'] == "CreateDistribution":
                cfId = recordEvent['detail']['responseElements']['distribution']['id']
                response = create_health_check_cf(cfId)
                if response == "The referenced protection does not exist.":
                    raise(Exception("Not shield protected, failing so SQS will retry later"))
            #Update Distro, disable distro is a parameter of requestParameter for an updateDistribution call
            if recordEvent['detail']['eventName'] == "UpdateDistribution":
                cfId = recordEvent['detail']['requestParameters']['id']
                #If distro is disabled per update distro recordEvent
                if recordEvent['detail']['requestParameters']['distributionConfig']['enabled'] == True:
                    create_health_check_cf(cfId)
                else:
                    delete_health_checks(cfId)
            #Changing Tags for an distro
            if recordEvent['detail']['eventName'] == "TagResource" or recordEvent['detail']['eventName'] == "UntagResource":
                cfId = recordEvent['detail']['requestParameters']['resource'].split("/",1)[1]
                cfDescribe = cf_client.get_distribution(
                        Id=cfId
                    )
                if cfDescribe['Distribution']['DistributionConfig']['Enabled'] == True:
                    create_health_check_cf(cfId)
                else:
                    delete_health_checks(cfId)
                    
