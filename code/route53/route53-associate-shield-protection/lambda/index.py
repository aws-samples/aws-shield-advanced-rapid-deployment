import sys
sys.path.insert(0,'./route53/route53-associate-shield-protection/lambda')
import boto3
import json
import cfnresponse
import botocore
import os
import logging

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

shield_client = boto3.client('shield')
def lambda_handler(event, context):
  responseData = {}
  logger.debug(event)
  try:
    resourceArn = event['ResourceProperties']['ResourceArn']
    requestType = event['RequestType']
    calculatedHCId = event['ResourceProperties']['CalculatedHCId']
  except botocore.exceptions.ClientError as error:
    cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
    return()    
  try:
    shieldProtection =  shield_client.describe_protection(
      ResourceArn=resourceArn)
    logger.debug(json.dumps(shieldProtection))
  except botocore.exceptions.ClientError as error:
    cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
    return()
  logger.debug("requestType")
  logger.debug(requestType)
  if not 'HealthCheckIds' in shieldProtection['Protection']:
    try:
      if requestType in ['Create','Update']:
        #logger.info("Associating Health Check")
        r = shield_client.associate_health_check(
          ProtectionId=shieldProtection['Protection']['Id'],
          HealthCheckArn="arn:aws:route53:::healthcheck/" + calculatedHCId
          )
    except botocore.exceptions.ClientError as error:
        logger.debug(error.response['Error'])
        cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
        return()      
  elif shieldProtection['Protection']['HealthCheckIds'] == []:
    logger.info("No Health Checks currently in place")
    try:
      if requestType in ['Create','Update']:
        #logger.info("Associating Health Check")
        r = shield_client.associate_health_check(
          ProtectionId=shieldProtection['Protection']['Id'],
          HealthCheckArn="arn:aws:route53:::healthcheck/" + calculatedHCId
          )
    except botocore.exceptions.ClientError as error:
        logger.debug(error.response['Error'])
        cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
        return()      
  else:
    #Confirm if provided HealthCheck is different than current Health CHeck
    if shieldProtection['Protection']['HealthCheckIds'][0] == calculatedHCId:
      logger.info("Existing Health Check already in place")
    else:
      logger.debug('Removing existing HC')
      for hc in shieldProtection['Protection']['HealthCheckIds']:
        try:
          response = shield_client.disassociate_health_check(
              ProtectionId=shieldProtection['Protection']['Id'],
              HealthCheckArn="arn:aws:route53:::healthcheck/" + hc
            )
        except botocore.exceptions.ClientError as error:
          cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
          return()
        try:
          if requestType in ['Create','Update']:
            logger.info("Associating Health Check")
            shield_client.associate_health_check(
            ProtectionId=shieldProtection['Protection']['Id'],
            HealthCheckArn="arn:aws:route53:::healthcheck/" + calculatedHCId
          )
        except botocore.exceptions.ClientError as error:
            cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
            return()
  cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "OK")
