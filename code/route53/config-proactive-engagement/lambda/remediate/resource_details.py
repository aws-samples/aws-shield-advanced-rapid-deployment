import json
import boto3
import os
import botocore
import logging

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

cloudfront_client = boto3.client('cloudfront')
shield_client = boto3.client('shield')
config_client = boto3.client('config')
elbv2_client = boto3.client('elbv2')
ec2_client = boto3.client('ec2')
accountId = os.environ['AccountId']
region = os.environ['AWS_REGION']

cloudfrontForceEnableEnhancedMetrics = os.environ['CloudFrontForceEnableEnhancedMetrics']

def ec2_details(resourceArn):
    response = {}
    logger.debug ("ec2_details")
    logger.debug (resourceArn)
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
    instanceId = instance['InstanceId']
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
    response['instanceId'] = instanceId
    response['resourceId'] = resourceArn.split("/")[-1]
    response['HealthCheckKey'] = os.environ['EIPEC2HealthCheckKey']
    logger.debug(response)
    return (response)
def elbv2_details(resourceArn):
    logger.debug (resourceArn)
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
    logger.debug ("tags")
    logger.debug (tags)
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
    logger.debug (distributionId)
    response = {}
    logger.debug ("cloudfrontForceEnableEnhancedMetrics")
    logger.debug (cloudfrontForceEnableEnhancedMetrics)
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

def get_deleted_resource_id_from_arn(resourceArn):
    print ("Start Get Deleted Resource ID from: ")
    print (resourceArn)
    response = {}
    if resourceArn.startswith('arn:aws:cloudfront'):
        response['resourceId'] = resourceArn.split('/')[1]
        response['resourceType'] = 'cloudfront'
        return (response)
    elif resourceArn.startswith ('arn:aws:elasticloadbalancing'):
        if 'loadbalancer/app/' in resourceArn:
            response['resourceId'] = resourceArn.split('/',1)[1]
            response['resourceType'] = 'alb'
            return (response)
    elif resourceArn.startswith('arn:aws:ec2:'):
        allocId = resourceArn.split('/')[1]
        address = ec2_client.describe_addresses(
            AllocationIds=
                [allocId])['Addresses'][0]
        if 'NetworkInterfaceId' in address.keys():
            eniDescription = ec2_client.describe_network_interfaces(
                NetworkInterfaceIds=[
                    address['NetworkInterfaceId']
                    ]
                    )['NetworkInterfaces'][0]['Description']
            #Determine if EIP is associated to an NLB
            if eniDescription.startswith('ELB net'):
                print ("Found NLB!")
                nlbId = elbv2_client.describe_load_balancers(
                    Names=[
                        eniDescription.split('/')[1],
                    ])['LoadBalancers'][0]['LoadBalancerArn'].split('/',1)[1]
                response['resourceId'] = nlbId
                response['resourceType'] = 'nlb'
                return (response)                
            elif "InstanceId" in address.keys():
                response['resourceId'] = address['InstanceId']
                response['resourceType'] = 'instance'
                return (response)
    else:    
        return ({})
    
    #ResourceArn: arn:aws:ec2:us-east-1:619607014791:eip-allocation/eipalloc-0745738c723bc950b | EIP on EC2
    #ResourceArn: arn:aws:cloudfront::619607014791:distribution/E2GVR1S0PP5KZ0
    #ResourceArn: arn:aws:elasticloadbalancing:us-east-1:619607014791:loadbalancer/app/prodapp/a183b0992714a862 | app/prodapp/a183b0992714a862
    return ()
def get_deleted_resource_details(protectionId):
    print ("Finding delete resource details for: " + protectionId)
    try:
        lastConfigurations = config_client.get_resource_config_history(
            resourceType='AWS::ShieldRegional::Protection',
            resourceId=protectionId,
            limit=10
        )['configurationItems']
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ResourceNotDiscoveredException':
            try:
                lastConfigurations = config_client.get_resource_config_history(
                    resourceType='AWS::Shield::Protection',
                    resourceId=protectionId,
                    limit=10
                )['configurationItems']
            except botocore.exceptions.ClientError as error:
                logger.debug(error.response['Error'])
                return (error.response['Error'])  
        else:
            logger.debug(error.response['Error'])
            return (error.response['Error'])
    logger.debug ("lastConfigurations!")
    logger.debug (lastConfigurations)
    for lastConfiguration in lastConfigurations:
        logger.debug("lastConfiguration")
        logger.debug(lastConfiguration)
        logger.debug(lastConfiguration['configuration'])
        if lastConfiguration['configuration'] != 'null':
            print ("Found it!")
            resourceArn = json.loads(lastConfiguration['configuration'])['ResourceArn']
            print (lastConfiguration)
            return({'ResourceArn':resourceArn})
            
    return ({"Error":{"Code":"NoConfigurationFounds","Message":"Resource History does not have a config in last 10 items"}})