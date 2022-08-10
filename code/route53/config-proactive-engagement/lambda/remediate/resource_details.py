import json
import boto3
import os
import botocore
import logging

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

cloudfront_client = boto3.client('cloudfront')
shield_client = boto3.client('shield')
elbv2_client = boto3.client('elbv2')
ec2_client = boto3.client('ec2')
accountId = os.environ['AccountId']
region = os.environ['AWS_REGION']

cloudfrontForceEnableEnhancedMetrics = os.environ['CloudFrontForceEnableEnhancedMetrics']

def ec2_details(resourceArn):
    response = {}
    print ("ec2_details")
    print (resourceArn)
    instance = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'network-interface.association.allocation-id',
                'Values': [
                    resourceArn.split('/')[-1]
                ]
            }
        ]
    )['Reservations'][0]['Instances'][0]
    if 'PublicDnsName' in instance:
        if instance['PublicDnsName'] == "":
            address = instance['PublicIpAddress'].replace('.','-')
            if region == 'us-east-1':
                response['defaultProbeFQDN'] = (f"ec2-{address}.compute-1.amazonaws.com")
            else:
                response['defaultProbeFQDN'] = (f"ec2-{address}.{region}.compute-1.amazonaws.com")
        else:
            response['defaultProbeFQDN'] = instance['PublicDnsName']
    response['resourceArn'] = resourceArn
    if 'Tags' in instance:
        tags = {}
        for t in instance['Tags']:
            tags[t['Key']] = t['Value']
        response['Tags'] = tags
    else:
        response['Tags'] = {}

    response['resourceId'] = resourceArn.split("/")[-1]
    response['HealthCheckKey'] = os.environ['EIPEC2HealthCheckKey']
    logger.debug(response)
    return (response)
def elbv2_details(resourceArn):
    print (resourceArn)
    response = {}
    lbDetails = elbv2_client.describe_load_balancers(
        LoadBalancerArns=[
            resourceArn
        ]
    )['LoadBalancers'][0]
    logger.debug ("lbDetails")
    logger.debug (lbDetails)
    tags_raw = elbv2_client.describe_tags(
        ResourceArns=[
            resourceArn
        ]
    )['TagDescriptions'][0]['Tags']
    tags = {}
    for t in tags_raw:
        tags[t['Key']] = t['Value']
    print ("tags")
    print (tags)
    response['resourceArn'] = resourceArn
    response['resourceId'] = resourceArn.split("/")[-1]
    response['defaultProbeFQDN'] = lbDetails['DNSName']
    response['Tags'] = tags
    if lbDetails['Type'] == 'application':
        response['HealthCheckKey'] = os.environ['ALBHealthCheckKey']
    else:
        response['HealthCheckKey'] = os.environ['NLBHealthCheckKey']
    logger.debug(response)
    return (response)

def cloudfront_details(distributionId):
    print (distributionId)
    response = {}
    print ("cloudfrontForceEnableEnhancedMetrics")
    print (cloudfrontForceEnableEnhancedMetrics)
    if cloudfrontForceEnableEnhancedMetrics == 'Yes':
        subStatus = cloudfront_client.get_monitoring_subscription(
            DistributionId=distributionId
        )['MonitoringSubscription']['RealtimeMetricsSubscriptionConfig']['RealtimeMetricsSubscriptionStatus']
        if subStatus == 'Disabled':
            cloudfront_client.create_monitoring_subscription(
                DistributionId=distributionId,
                MonitoringSubscription={
                    'RealtimeMetricsSubscriptionConfig': {
                        'RealtimeMetricsSubscriptionStatus': 'Enabled'
                    }
                }
            )
    try:
        distribution = cloudfront_client.get_distribution(
            Id=distributionId)['Distribution']
    except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error'])
        response['Error'] = error.response['Error']
        return (response)
    resourceArn = distribution['ARN']
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
    response['resourceId'] = resourceArn.split("/")[-1]
    response['resourceArn'] = resourceArn
    response['defaultProbeFQDN'] = distribution['DomainName']
    response['Tags'] = tags
    response['HealthCheckKey'] = os.environ['CloudfrontHealthCheckKey']
    logger.debug(response)
    return (response)
