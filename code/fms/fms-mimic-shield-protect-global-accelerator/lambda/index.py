import sys
sys.path.insert(0,'./fms/lambda/global-accelerator-protection')

import boto3
import os
import botocore
import logging
import json
import copy
import cfnresponse
from tag_check import tag_check

logger = logging.getLogger('shieldProtection')
logger.setLevel('DEBUG')

ga_client = boto3.client('globalaccelerator',region_name='us-west-2')
ga_paginator = ga_client.get_paginator('list_accelerators')
shield_client = boto3.client('shield')
shield_paginator = shield_client.get_paginator('list_protections')

def lambda_handler(event, context):
  responseData = {}
  #List of Hosted Zones
  try:
    accelerators = (ga_paginator.paginate().build_full_result())['Accelerators']
    logger.debug(accelerators)
  except botocore.exceptions.ClientError as error:
    logger.error(error.response['Error']['Message'])
    if 'RequestType' in event:
      responseData['Error'] = error.response['Error']
      cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "PaginateAccleratorsFailed")
    return (error.response['Error']['Message'])
  #List of Shield Protected Resources
  try:
    shieldProtected = (shield_paginator.paginate().build_full_result())['Protections']
    logger.debug(shieldProtected)
  except botocore.exceptions.ClientError as error:
    logger.error(error.response['Error']['Message'])
    if 'RequestType' in event:
      responseData['Error'] = error.response['Error']
      cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "PaginateShieldprotectionFailed")
    return (error.response['Error']['Message'])

  protectedArns = []
  protectionIdList = {}
  #Build a list of just resource ARN's for Shield Protected resouces
  for s in shieldProtected:
      protectedArns.append(s['ResourceArn'])
      protectionIdList[s['ResourceArn']] = s['Id']
  #If no hosted zones exist, stop gracefully now
  if accelerators == []:
      logger.info("No Global Accelerators")
      return ()
  else:
      #For each Hosted Zone
      for accelerator in accelerators:
          logger.debug(accelerator)
          acceleratorArn = accelerator['AcceleratorArn']
          try:
            tags = ga_client.list_tags_for_resource(
              ResourceArn=acceleratorArn
              )['Tags']
          except botocore.exceptions.ClientError as error:
            if 'RequestType' in event:
              responseData['Error'] = error.response['Error']
              cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "listTagsFailed")
            logger.error(error.response['Error']['Message'])
            return (error.response['Error']['Message'])
          #Check resource tags vs. checkTags as include/exclude logic
          tagResults = tag_check(tags)
          #If the hosted Zone is current Shield Protected
          isProtected = acceleratorArn in protectedArns
          #If tags match and it isn't protected
          if tagResults == True and isProtected == False:
              logger.info ("Not protected and should be")
              try:
                shield_client.create_protection(
                    Name=accelerator['Name'],
                    ResourceArn=acceleratorArn)
              except botocore.exceptions.ClientError as error:
                logger.error(error.response['Error']['Message'])
                if 'RequestType' in event:
                  responseData['Error'] = error.response['Error']
                  cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "ShieldCreateProtectionFailed")
                return (error.response['Error']['Message'])
          #If tags do not match requirements and it is Shield protected
          elif tagResults == False and isProtected == True:
              logger.info ("Protected and should not be")
              protectionId = protectionIdList[acceleratorArn]
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
      if 'RequestType' in event:
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "GAProtectionSucceeded")