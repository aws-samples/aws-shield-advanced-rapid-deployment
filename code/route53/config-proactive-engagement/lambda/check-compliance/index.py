import sys
#sys.path.insert(0,'./route53/config-proactive-engagement/lambda/check-compliance')
sys.path.insert(0,'./route53/config-proactive-engagement/lambda/common')
import os
import json
import boto3
import botocore
import logging

from sqs_tasks import *
from resource_details import *
#from resource_checks import *
from tag_check import tag_check
from datetime import datetime

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')


#Boto3 clients
config_client = boto3.client('config')
cloudfront_client = boto3.client('cloudfront')
ec2_client = boto3.client('ec2')
elbv2_client = boto3.client('elbv2')
shield_client = boto3.client('shield')
route53_client = boto3.client('route53')
#aga_client = boto3.client('globalaccelerator',region_name='us-west-2')

inScopeResources = [
    "cloudfront"
    ,"instance"
    ,"alb"
    ,"nlb"
    ,"clb"
    #,"hostedzone",
    #,"globalaccelerator"
    ]
def config_eval_put(evaluation,resultToken):
    logger.info ("evaluation['ComplianceType']s: " + evaluation['ComplianceType'])
    logger.info ("evaluation['Annotation']: " + evaluation['Annotation'])
    try:
        response = config_client.put_evaluations(
              Evaluations=[
                  evaluation
              ],
              ResultToken=resultToken
            )
        logger.debug("Config Results")
        logger.debug(response)
        return()
    except botocore.exceptions.ClientError as error:
        return (error.response)

def lambda_handler(event, context):
    if not 'invokingEvent' in event.keys():
        return()
    invokingEvent = json.loads(event['invokingEvent'])
    if "messageType" in invokingEvent:
        if invokingEvent['messageType'] == 'ScheduledNotification':
            return()
    logger.debug ("Event")
    logger.debug (json.dumps(event))
    logger.debug ("InvokingEvent")
    logger.debug (json.dumps(invokingEvent))
    resultToken = event['resultToken']
    resourceId = invokingEvent['configurationItem']['resourceId']
    configResourceType = invokingEvent['configurationItem']['resourceType']
    evaluation = {
        'ComplianceResourceType': configResourceType,
        'ComplianceResourceId': resourceId,
        'ComplianceType': "",
        'Annotation': " ",
        'OrderingTimestamp': datetime.now()
    }
    if invokingEvent['configurationItem']['configurationItemStatus'] == 'ResourceDeleted':
        protectionId = invokingEvent['configurationItem']['ARN'].split('/')[-1]
        rawResourceArn = get_deleted_resource_arn(protectionId)['ResourceArn']
        logger.debug("rawResourceArn")
        logger.debug(rawResourceArn)
    else:
        rawResourceArn = invokingEvent['configurationItem']['configuration']['ResourceArn']
        relationships = invokingEvent['configurationItem']['relationships']
        region = invokingEvent['configurationItem']['awsRegion']
        accountId = event['accountId']

    resourceDetails = build_resource_details(rawResourceArn)
    logger.debug("resourceDetails")
    logger.debug(json.dumps(resourceDetails))
    resourceType = resourceDetails['resourceType']
    if not resourceType in inScopeResources:
        evaluation['ComplianceType'] = "NOT_APPLICABLE"
        evaluation['Annotation'] == "Resource " + resourceType + " not supported"
        response = config_eval_put(evaluation, resultToken)
        return ()
    stackSuffix = resourceDetails['stackSuffix']
    resourceArn = resourceDetails['resourceArn']
    resourceId = resourceDetails['resourceId']

    if invokingEvent['configurationItem']['configurationItemStatus'] == 'ResourceDeleted':
        msg_body = {"action": "Delete", "resourceId": resourceId, "stackSuffix": stackSuffix,'resourceType': resourceType}
        send_cfn_sqs_message(msg_body)
        evaluation['ComplianceType'] = 'NOT_APPLICABLE'
        evaluation['Annotation'] = 'DeletedResource'
        response = config_eval_put(evaluation, resultToken)
        return ()
    tags = []
    tags = resource_tags(resourceArn, resourceType)

    logger.info ("####################################################################################")
    logger.info ("ResourceType: " + resourceType)
    logger.info ("ResourceArn: " + resourceArn)
    logger.info ("####################################################################################")
    #for k in list(shieldProtectionDetails.keys()):
        #logger.debug (k + ": " + str(shieldProtectionDetails[k]))
    tagCheck = tag_check(tags, True)
    logger.debug ("TagCheckResults: " + str (tagCheck))
    if tagCheck == False:
        evaluation['ComplianceType'] = "NOT_APPLICABLE"
        evaluation['Annotation'] == 'Out of Scope based on tags'
        response = config_eval_put(evaluation, resultToken)
        return ()
    #If there are no health checks associated with the Shield ID
    if invokingEvent['configurationItem']['configuration']['HealthCheckIds'] == []:
        evaluation['ComplianceType'] = 'NON_COMPLIANT'
        evaluation['Annotation'] = 'No HealthCheck associated with ' + resourceArn
    else:
        hcId = invokingEvent['configurationItem']['configuration']['HealthCheckIds'][0]
        try:
            route53_client.get_health_check(HealthCheckId=hcId)
            evaluation['ComplianceType'] = 'COMPLIANT'
            evaluation['Annotation'] = "Health Check Found: " + hcId
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'NoSuchHealthCheck':
                evaluation['ComplianceType'] = 'NON_COMPLIANT'
                evaluation['Annotation'] = 'Associated HealthCheck ' + hcId + ' does not exist'
    response = config_eval_put(evaluation, resultToken)
    return ()
