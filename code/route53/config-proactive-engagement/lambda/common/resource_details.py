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
        InstanceIds=[resourceArn.split('/')[-1]]
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

def get_shield_protection_details(protectionId):
    response = {}
    try:
        shieldProtectionDetails = shield_client.describe_protection(
            ProtectionId =protectionId)['Protection']
        logger.debug ("ShieldProtectionDetails")
        logger.debug (shieldProtectionDetails)
        return (shieldProtectionDetails)
    except botocore.exceptions.ClientError as error:
        logger.debug ("ShieldProtectionDetails - Error")
        logger.error(error.response)
        return (error.respone['Error']['Code'])

def build_resource_details(resourceArn):
    print ("Start Get Deleted Resource ID from: ")
    print (resourceArn)
    response = {}
    if resourceArn.startswith('arn:aws:cloudfront'):
        logger.debug("Found CloudFront")
        resourceId = resourceArn.split('/')[1]
        response['stackSuffix'] = resourceId
        response['resourceArn'] = resourceArn
        response['resourceId'] = resourceId
        response['resourceType'] = 'cloudfront'
        return (response)
    elif resourceArn.startswith ('arn:aws:elasticloadbalancing'):
        logger.debug("Found ELBV2")
        if 'loadbalancer/app/' in resourceArn:
            logger.debug("Found ALB")
            resourceId = resourceArn.split('/',1)[1]
            response['stackSuffix'] = resourceId
            response['resourceArn'] = resourceArn
            response['resourceId'] = resourceId
            response['resourceType'] = 'alb'
            return (response)
    elif resourceArn.startswith('arn:aws:ec2:'):
        logger.debug("Found EIP Something")
        allocId = resourceArn.split('/')[1]
        address = ec2_client.describe_addresses(
            AllocationIds=
                [allocId])['Addresses'][0]
        logger.debug('Addresses response')
        logger.debug(address)
        if 'NetworkInterfaceId' in address.keys():
            logger.debug("Has NetworkInterfaceId")
            eniDescription = ec2_client.describe_network_interfaces(
                NetworkInterfaceIds=[
                    address['NetworkInterfaceId']
                    ]
                    )['NetworkInterfaces'][0]['Description']
            #Determine if EIP is associated to an NLB
            if eniDescription.startswith('ELB net'):
                logger.debug("Found NLB")
                elbv2Arn = elbv2_client.describe_load_balancers(
                    Names=[
                        eniDescription.split('/')[1],
                    ])['LoadBalancers'][0]['LoadBalancerArn']
                resourceId = elbv2Arn.split('/',1)[1]
                response['stackSuffix'] = resourceId
                response['resourceArn'] = elbv2Arn
                response['resourceId'] = resourceId
                response['resourceType'] = 'nlb'
                return (response)                
            elif "InstanceId" in address.keys():
                logger.debug("Found Instance")
                response['stackSuffix'] = "-".join([address['InstanceId'],allocId])
                response['resourceArn'] = "".join(["arn:aws:ec2:",region, ":", accountId,":instance/",address['InstanceId']])
                response['resourceId'] = allocId
                response['resourceType'] = 'instance'
                return (response)
        else:
            logger.debug("Is NonAttachedEIP")
            response['resourceType'] = 'NonAttachedEIP'
            return (response)
    elif resourceArn.startswith('arn:aws:route53'):
        response['resourceType'] = 'hostedzone'
        resourceId = resourceArn.split('/')[1]
        response['resourceId'] = resourceId
        response['stackSuffix'] = resourceId
        return (response)
    else:    
        response = {
            "resourceType":"unknown",
            "resourceId": "unknown",
            "stackSuffix": "unknown"
        }
        return (response)
    
    #ResourceArn: arn:aws:ec2:us-east-1:619607014791:eip-allocation/eipalloc-0745738c723bc950b | EIP on EC2
    #ResourceArn: arn:aws:cloudfront::619607014791:distribution/E2GVR1S0PP5KZ0
    #ResourceArn: arn:aws:elasticloadbalancing:us-east-1:619607014791:loadbalancer/app/prodapp/a183b0992714a862 | app/prodapp/a183b0992714a862
    return ()

def get_deleted_resource_arn(protectionId):
    logger.info ("Finding delete resource details for: " + protectionId)
    #There is no easy way to know if it is a regional or global resource, so we try regional first, then global
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
    logger.debug ("Last Configurations")
    logger.debug (lastConfigurations)
    for lastConfiguration in lastConfigurations:
        if lastConfiguration['configuration'] != 'null':
            try:
                resourceArn = json.loads(lastConfiguration['configuration'])['ResourceArn']
                return({'ResourceArn':resourceArn})
            except:
                continue
    #We only reach here if nothing returned from any of the last 10 config records
    return ({"Error":{"Code":"NoConfigurationFounds","Message":"Resource History does not have a config in last 10 items"}})

def resource_tags(resourceArn, resourceType):
    logger.debug("Begin resource Tag enumerate")
    logger.debug ("ResourceArn:" + resourceArn)
    logger.debug ("ResourceType:" + resourceType)
    if resourceType == "cloudfront":
        tags = cloudfront_client.list_tags_for_resource(
            Resource=resourceArn
        )['Tags']['Items']
    #ELBv2 (ALB or NLB)
    #elif resourceType == "AWS::GlobalAccelerator::Accelerator":
        #tags = aga_client.list_tags_for_resource(
            #ResourceArn=resourceArn
            #)['Tags']
    elif resourceType in ['alb','nlb']:
        tags = elbv2_client.describe_tags(
            ResourceArns=[resourceArn]
            )['TagDescriptions'][0]['Tags']
    elif resourceType == 'instance':
        print ("Found Instance")
        instanceId = resourceArn.split('/')[-1]

        tags = ec2_client.describe_tags(
            Filters=[
                {
                    'Name': 'resource-type',
                    'Values': [
                        'instance'
                    ]
                },
                {
                    'Name': 'resource-id',
                    'Values': [
                        instanceId
                    ]
                }
            ]
        )['Tags']
        for t in tags:
            t.pop('ResourceId')
            t.pop('ResourceType')
    else:
        print ("Not Supported resource")
        return ("Not Supported resource")
    print ("Tag Results")
    for t in tags:
        print ("Name: " + t['Key'] + " | Value: " + t['Value'])
        print ()
    return (tags)
