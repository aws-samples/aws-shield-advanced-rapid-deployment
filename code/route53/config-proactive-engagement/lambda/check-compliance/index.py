import sys
sys.path.insert(0,'./route53/config-proactive-engagement/lambda/check-compliance')
sys.path.insert(0,'./route53/config-proactive-engagement/lambda/common')
import os
import json
import boto3
import botocore
from resource_checks import *
from tag_check import tag_check
from datetime import datetime

#Boto3 clients
config_client = boto3.client('config')
cloudfront_client = boto3.client('cloudfront')
ec2_client = boto3.client('ec2')
elbv2_client = boto3.client('elbv2')
shield_client = boto3.client('shield')
route53_client = boto3.client('route53')
aga_client = boto3.client('globalaccelerator',region_name='us-west-2')
inScopeResources = [
    "cloudfront",
    "instance",
    "alb",
    "nlb",
    "clb",
    "hostedzone",
    "globalaccelerator"
    ]
def config_eval_put(evaluation,resultToken):
    response = config_client.put_evaluations(
          Evaluations=[
              evaluation
          ],
          ResultToken=resultToken
        )
    return (response)
def lambda_handler(event, context):

    invokingEvent = json.loads(event['invokingEvent'])
    print (json.dumps(event))
    print (invokingEvent)
    resultToken = event['resultToken']
    resourceId = invokingEvent['configurationItem']['resourceId']
    resourceArn = invokingEvent['configurationItem']['configuration']['ResourceArn']
    configResourceType = invokingEvent['configurationItem']['resourceType']
    region = invokingEvent['configurationItem']['awsRegion']
    accountId = event['accountId']
    #evaluation['Annotation'] = resourceArn
    #evaluation['ComplianceType'] = ""
    secondardResource = ""
    tags = []


    shieldProtectionDetails = identify_resource_type(resourceId)
    print ("shieldProtectionDetails")
    for k in list(shieldProtectionDetails.keys()):
        print (k + ": " + str(shieldProtectionDetails[k]))
    tags = resource_tags(shieldProtectionDetails['ResourceArn'],shieldProtectionDetails['ResourceType'])
    resourceType = shieldProtectionDetails['ResourceType']
    evaluation = {
        'ComplianceResourceType': configResourceType,
        'ComplianceResourceId': resourceId,
        'ComplianceType': "",
        'Annotation': " ",
        'OrderingTimestamp': datetime.now()
    }
    #Not applicable if the resource is being deleted.  No need to check anything else
    if invokingEvent['configurationItem']['configurationItemStatus'] == 'ResourceDeleted':
        evaluation['ComplianceType'] = 'NOT_APPLICABLE'
        evaluation['Annotation'] = 'DeletedResource'
        response = config_eval_put(evaluation, resultToken)
        return (response)
    print ("####################################################################################")
    print ("ResourceType: " + resourceType)
    print ("ResourceArn: " + resourceArn)
    print ("ResourceId: " + resourceId)
    print ("####################################################################################")
    for k in list(shieldProtectionDetails.keys()):
        print (k + ": " + str(shieldProtectionDetails[k]))
    print ("####################################################################################")
    ###########
    tagCheck = tag_check(tags, True)
    print ("####################################################################################")
    print ("TagCheckResults: " + str (tagCheck))
    if tagCheck == True and evaluation['ComplianceType'] == "":
        #If there are no health checks associated with the Shield ID
        if invokingEvent['configurationItem']['configuration']['HealthCheckIds'] == []:
            evaluation['ComplianceType'] = 'NON_COMPLIANT'
            evaluation['Annotation'] = 'No HealthCheck associated with ' + shieldProtectionDetails['ResourceArn']
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
    #If evaluation['ComplianceType']s not already defined, the resource is not applicable
    elif evaluation['ComplianceType'] == "":
          evaluation['ComplianceType'] = 'NOT_APPLICABLE'
          evaluation['Annotation'] = 'Tags do not match'
    #If the shield protection is for one resource but it is related to another, e.g. an Instance for an EIP
    if secondardResource != "":
        evaluation['Annotation']  = evaluation['Annotation'] + " | " + secondardResource
    print ("evaluation['ComplianceType']s: " + evaluation['ComplianceType'])
    print ("evaluation['Annotation']: " + evaluation['Annotation'])
    if not resourceType in inScopeResources:
        evaluation['ComplianceType'] = 'NOT_APPLICABLE'
        evaluation['Annotation'] = "Resource type not in scope"
    print ("####################################################################################")
    print ("Evaluation")
    for k in list(evaluation.keys()):
        print (evaluation[k])

        print (k + ": " + str(evaluation[k]))
    response = config_eval_put(evaluation,resultToken)
    print ("####################################################################################")
    print ("Config Response")
    print (response)
