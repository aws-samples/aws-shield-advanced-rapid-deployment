import sys
sys.path.insert(0,'./route53/cloudfront-config-proactive-engagement/lambda/check-compliance')
import os
from tag_check import tag_check
import json
import boto3
from datetime import datetime
config_client = boto3.client('config')
shield_client = boto3.client('shield')
cloudfront_client = boto3.client('cloudfront')

def lambda_handler(event, context):
    invokingEvent = json.loads(event['invokingEvent'])
    #print (json.dumps(event))
    #print (invokingEvent)
    resultToken = event['resultToken']
    resourceType = invokingEvent['configurationItem']['resourceType']
    resourceId = invokingEvent['configurationItem']['resourceId']
    resourceArn = invokingEvent['configurationItem']['configuration']['ResourceArn']
    annotation = resourceArn
    if invokingEvent['configurationItem']['configurationItemStatus'] == 'ResourceDeleted':
        configResult = 'NOT_APPLICABLE'
        annotation = 'DeletedResource'
    else:
        if invokingEvent['configurationItem']['configuration']['ResourceArn'].startswith("arn:aws:cloudfront::"):
            tags = cloudfront_client.list_tags_for_resource(
                Resource=resourceArn
            )['Tags']['Items']
        print (tags)
        tagCheck = tag_check(tags, True)
        if tagCheck == True:
            if invokingEvent['configurationItem']['configuration']['HealthCheckIds'] == []:
                configResult = 'NON_COMPLIANT'
                annotation = 'No HealthCheck associated with ' + resourceArn
            else:
                configResult = 'COMPLIANT'
                annotation = invokingEvent['configurationItem']['configuration']['HealthCheckIds'][0]
        else:
          configResult = 'NOT_APPLICABLE'
          annotation = 'Tags do not match'
    config_client.put_evaluations(
      Evaluations=[
          {
              'ComplianceResourceType': resourceType,
              'ComplianceResourceId': resourceId,
              'ComplianceType': configResult,
              'Annotation': annotation,
              'OrderingTimestamp': datetime.now()
          },
      ],
      ResultToken=resultToken
    )
