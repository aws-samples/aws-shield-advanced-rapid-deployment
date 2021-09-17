import sys
sys.path.insert(0,'./route53/lambda/albHC')
import json
import boto3
import os
import cfnresponse
import logging
import botocore

from create_health_check_alb import create_health_check_alb
from delete_health_checks import delete_health_checks


logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

sqs_client = boto3.client('sqs')
elbv2_client = boto3.client('elbv2')

queueUrl = os.environ['sqsQueueURL']
accountId = os.environ['AccountId']

def lambda_handler(event, context):
    logger.debug(event)
    responseData = {}
    #If called by CloudFormation for create, update or delete actions
    if 'RequestType' in event:
        try:
            elbv2s= elbv2_client.describe_load_balancers()
        except botocore.exceptions.ClientError as error:
            cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "CustomResourcePhysicalID")
            logger.error(error.response['Error']['Message'])
            return ()
        if (event['RequestType'] == 'Create' or event['RequestType'] == 'Update'):
            for elb in elbv2s['LoadBalancers']:
                if elb['Type'] == 'application':
                    logger.info("Created synthetic create message so we try again later but CFN can finish")
                    message = {
                              "detail": {
                                  "eventName": "CreateLoadBalancer",
                                  "requestParameters": {
                                    "type": "application"
                                    },
                                "responseElements": {
                                    "loadBalancers": [
                                        {
                                          "loadBalancerArn": elb['LoadBalancerArn']
                                        }
                                  ]
                                }
                              }
                            }
                    response = sqs_client.send_message(
                        QueueUrl=queueUrl,
                        MessageBody=json.dumps(message),
                        DelaySeconds=5
                        )
                    logger.debug(response)
                else:
                    logger.info("Skipping: " + elb['Type'])
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CustomResourcePhysicalID")
        elif event['RequestType'] == 'Delete':
            for elb in elbv2s['LoadBalancers']:
                if elb['Type'] == 'application':
                    delete_health_checks(elb['LoadBalancerArn'].split('/')[2])
                else:
                    logger.info("LB Tye Mismatch. Skipping: " + elb['Type'])
            responseData = {}
            responseData['Data'] = "OK"
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CustomResourcePhysicalID")
    #This is a message from SQS via CloudWatch Events
    elif 'Records' in event:
        #If batching is ever added, by record
        for record in event['Records']:
            recordEvent = json.loads(record['body'])
            logger.debug(recordEvent)
            logger.info(recordEvent['detail']['eventName'])
            if recordEvent['detail']['eventName'] == "CreateLoadBalancer":
                if ('type' in recordEvent['detail']['requestParameters']):
                    if (recordEvent['detail']['requestParameters']['type'] == 'application'):
                        for lb in recordEvent['detail']['responseElements']['loadBalancers']:
                            response = create_health_check_alb(lb['loadBalancerArn'])
                            if response == "The referenced protection does not exist.":
                                raise Exception("Not Shield Protected, exiting ungracefully for SQS retry to check later")
                            elif response == "StackFailure":
                                raise Exception("Stack Failed, exiting ungracefully for SQS retry to try again later")
            elif recordEvent['detail']['eventName'] == "DeleteLoadBalancer":
                if ('loadBalancerArn' in recordEvent['detail']['requestParameters']):
                    lbArn = recordEvent['detail']['requestParameters']['loadBalancerArn']
                    lbType = lbArn.split('/')[1]
                    if lbType == 'app':
                        logger.info("Deleting Checks for ALB")
                        delete_health_checks(lbArn.split('/')[2])
                    else:
                        logger.info("Skipping: " + lbType)
            #Changing Tags for an ALB
            elif recordEvent['detail']['eventName'] == "AddTags":
                lbArn = recordEvent['detail']['requestParameters']['resourceArns'][0]
                lbType = lbArn.split('/')[1]
                if lbType == 'app':
                    logger.info("AddTagTriggered")
                    response = create_health_check_alb(lbArn)
                    if response == "The referenced protection does not exist.":
                        raise Exception("Not Shield Protected, exiting ungracefully for SQS retry to check later")
                    elif response == "StackFailure":
                        raise Exception("Stack Failed, exiting ungracefully for SQS retry to try again later")
                    
                else:
                    logger.info("Skipping: " + lbType)
            elif recordEvent['detail']['eventName'] == "RemoveTags":
                lbArn = recordEvent['detail']['requestParameters']['resourceArns'][0]
                lbType = lbArn.split('/')[1]
                if lbType == 'app':
                    response = create_health_check_alb(lbArn)
                    if response == "The referenced protection does not exist.":
                        raise Exception("Not Shield Protected, exiting ungracefully for SQS retry to check later")
                    elif response == "StackFailure":
                        raise Exception("Stack Failed, exiting ungracefully for SQS retry to try again later")
                else:
                    logger.info("Skipping: " + lbType)