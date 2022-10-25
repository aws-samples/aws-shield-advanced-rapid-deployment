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
elbv2_client = boto3.client('elbv2')
def lambda_handler(event, context):
  responseData = {}
  logger.debug(event)
  #Extract details from inbound event
  try:
    resourceArn = event['ResourceProperties']['ResourceArn']
    region = os.environ['AWS_REGION']
    accountId =  event['ServiceToken'].split(':')[4]
    requestType = event['RequestType']
    calculatedHCId = event['ResourceProperties']['CalculatedHCId']
    logger.debug ("ResourceArn: " + resourceArn)
    logger.debug ("Region: " + region)
    logger.debug ("AccountId: " + str(accountId))
    logger.debug ("CalculatedHCId: " + calculatedHCId)
  except botocore.exceptions.ClientError as error:
    cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
    return()
  #try:
  if requestType == 'Delete':
    logger.debug("Delete: No Action Needed")
    cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "OK")
    return()
  if resourceArn.startswith("net/"):
    logger.info ("Found NLB, getting EIP Arns instead")
    #arn:aws:elasticloadbalancing:us-east-1:619607014791:loadbalancer/net/nlb1/e92328cef5a71f70
    nlbArn = "".join(["arn:aws:elasticloadbalancing:", region, ":", accountId, ":loadbalancer/",resourceArn])
    lbAzDetails = elbv2_client.describe_load_balancers(
        LoadBalancerArns=[
            nlbArn
        ]
    )['LoadBalancers'][0]['AvailabilityZones']
    resourceArn = []
    for az in lbAzDetails:
      for a in az['LoadBalancerAddresses']:
        resourceArn.append('arn:aws:ec2:' + region + ':' + accountId + ':eip-allocation/' +a['AllocationId'])
  if isinstance(resourceArn,str):
    try:
      shieldProtections = []
      shieldProtections.append(shield_client.describe_protection(
        ResourceArn=resourceArn))
      logger.debug(json.dumps(shieldProtections))
    except botocore.exceptions.ClientError as error:
      cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
      return()
  else:
    shieldProtections = []
    for rArn in resourceArn:
      try:
        shieldProtections.append(shield_client.describe_protection(
          ResourceArn=rArn))
        logger.debug(json.dumps(shieldProtections))
      except botocore.exceptions.ClientError as error:
        cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
        return()
  logger.debug("requestType")
  logger.debug(requestType)
  #For create and update requests
  for shieldProtection in shieldProtections:
    if requestType in ['Create','Update']:
        #If there is not and has not been a health check associated, association inputted health check
        if not 'HealthCheckIds' in shieldProtection['Protection']:
          try:
              #logger.info("Associating Health Check")
              r = shield_client.associate_health_check(
                ProtectionId=shieldProtection['Protection']['Id'],
                HealthCheckArn="arn:aws:route53:::healthcheck/" + calculatedHCId
                )
          except botocore.exceptions.ClientError as error:
              logger.debug(error.response['Error'])
              cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
              return()
        #If some other health check is or was associated, associate the inputted health check now
        elif shieldProtection['Protection']['HealthCheckIds'] == []:
          logger.info("No Health Checks currently in place")
          try:
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
          #Remove existing health checks before adding inputted health check
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
                  logger.info("Associating Health Check")
                  shield_client.associate_health_check(
                  ProtectionId=shieldProtection['Protection']['Id'],
                  HealthCheckArn="arn:aws:route53:::healthcheck/" + calculatedHCId
                  )
              except botocore.exceptions.ClientError as error:
                  cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
                  return()
    #If CloudFormation is signalling delete, disassociate the inputtted health check only if found
    elif requestType in ['Delete']:
      if 'HealthCheckIds' in shieldProtection['Protection']:
        for hc in shieldProtection['Protection']['HealthCheckIds']:
          try:
              if calculatedHCId == hc:
                    response = shield_client.disassociate_health_check(
                        ProtectionId=shieldProtection['Protection']['Id'],
                        HealthCheckArn="arn:aws:route53:::healthcheck/" + hc
                      )
          except botocore.exceptions.ClientError as error:
            cfnresponse.send(event, context, cfnresponse.FAILED, {"Message": error.response['Error']['Message']}, "")
            return()

  #Signal Success if we didn't signal failure along the way
  cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "OK")
