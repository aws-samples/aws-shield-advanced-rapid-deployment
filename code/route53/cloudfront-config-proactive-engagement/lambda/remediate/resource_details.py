import json
import boto3
import os
import botocore
import logging

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

cloudfront_client = boto3.client('cloudfront')
shield_client = boto3.client('shield')

accountId = os.environ['AccountId']

def cloudfront_details(protectionId):
    print (protectionId)
    response = {}
    try:
        shieldProtection = shield_client.describe_protection(
          ProtectionId =protectionId)
    except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error'])
        response['Error'] = error.response['Error']
        return (response)
    resourceArn = shieldProtection['Protection']['ResourceArn']
    distributionId = resourceArn.split('/')[-1]
    distribution = cloudfront_client.get_distribution(
        Id=distributionId)['Distribution']
    try:
      tags_raw = cloudfront_client.list_tags_for_resource(
        Resource=resourceArn)['Tags']['Items']
    except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error'])
        response['Error'] = error.response['Error']
        return (response)
    tags = {}
    for t in tags_raw:
        tags[t['Key']] = t['Value']
    cloudfrontHCKey = os.environ['CloudfrontHealthCheckKey']
    response['resourceArn'] = resourceArn
    response['defaultProbeFQDN'] = distribution['DomainName']
    response['ShieldProtection'] = shieldProtection
    response['Tags'] = tags
    response['HealthCheckKey'] = cloudfrontHCKey
    response['ResourceId'] = distributionId
    logger.debug(response)
    return (response)