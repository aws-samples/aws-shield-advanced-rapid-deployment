import sys
sys.path.insert(0,'./fms/lambda/r53-hosted-zone-protection')
import boto3
import os
import botocore
import logging
import json
import copy
import cfnresponse
from index import tag_check

logger = logging.getLogger('shieldProtection')
logger.setLevel('DEBUG')

r53_client = boto3.client('route53')
r53_paginator = r53_client.get_paginator('list_hosted_zones')
shield_client = boto3.client('shield')
shield_paginator = shield_client.get_paginator('list_protections')

def lambda_handler(event, context):
  responseData = {}
  try:
    #List of Hosted Zones
    hostedZones = (r53_paginator.paginate().build_full_result())['HostedZones']
    logger.debug(hostedZones)
    #List of Shield Protected Resources
    shieldProtected = (shield_paginator.paginate().build_full_result())['Protections']
    logger.debug(shieldProtected)
  except botocore.exceptions.ClientError as error:
    logger.error(error.response['Error']['Message'])
    if 'RequestType' in event:
      responseData['Error'] = error.response['Error']
      cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "PaginateFailed")

    return (error.response['Error']['Message'])

  protectedArns = []
  protectionIdList = {}
  #Build a list of just resource ARN's for Shield Protected resouces
  for s in shieldProtected:
      protectedArns.append(s['ResourceArn'])
      protectionIdList[s['ResourceArn']] = s['Id']
  #If no hosted zones exist, stop gracefully now
  if hostedZones == []:
      logger.info("No Hosted Zones")
      return ()
  else:
      #For each Hosted Zone
      for zone in hostedZones:
          logger.info(zone)
          zoneId = zone['Id'].split('/')[2]
          zoneArn = "arn:aws:route53:::hostedzone/" + zoneId
          try:
            r = r53_client.list_tags_for_resources(
              ResourceType='hostedzone',
              ResourceIds=[
                  zoneId
                  ])
          except botocore.exceptions.ClientError as error:
            logger.error(error.response['Error']['Message'])
            if 'RequestType' in event:
              responseData['Error'] = error.response['Error']
              cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "ListTagsFailed")

            return (error.response['Error']['Message'])
          #Check resource tags vs. checkTags as include/exclude logic
          tagResults = tag_check(r['ResourceTagSets'][0]['Tags'])
          #If the hosted Zone is current Shield Protected
          isProtected = zoneArn in protectedArns
          #If tags match and it isn't protected
          if tagResults == True and isProtected == False:
              logger.info ("Not protected and should be")
              try:
                shield_client.create_protection(
                    Name=zoneId,
                    ResourceArn=zoneArn)
              except botocore.exceptions.ClientError as error:
                logger.error(error.response['Error']['Message'])
                if 'RequestType' in event:
                  responseData['Error'] = error.response['Error']
                  cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "ShieldCreateProtectionFailed")
                return (error.response['Error']['Message'])
          #If tags do not match requirements and it is Shield protected
          elif tagResults == False and isProtected == True:
              logger.info ("Protected and should not be")
              protectionId = protectionIdList['zoneArn']
              try:
                shield_client.delete_protection(
                    ProtectionId=protectionId)
              except botocore.exceptions.ClientError as error:
                logger.error(error.response['Error']['Message'])
                if 'RequestType' in event:
                  responseData['Error'] = error.response['Error']
                  cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "ShieldDeleteProtectionFailed")
                return (error.response['Error']['Message'])
          #The other possible results require no change/action for this resource
          #Is passed check tags and is already protected
          #Did not pass check tags and is not protected
          else:
              logger.info("No change to protection needed")
      #Signal CFN if this is a create, or update
      if 'RequestType' in event:
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CustomResourcePhysicalID")