import boto3
shield_client = boto3.client('shield')
ec2_client = boto3.client('ec2')
elbv2_client = boto3.client('elbv2')
cloudfront_client = boto3.client('cloudfront')

def resource_tags(resourceArn, resourceType):

    if resourceType == "cloudfront":
        tags = cloudfront_client.list_tags_for_resource(
            Resource=resourceArn
        )['Tags']['Items']
    #ELBv2 (ALB or NLB)
    elif resourceType == "AWS::GlobalAccelerator::Accelerator":
        tags = aga_client.list_tags_for_resource(
            ResourceArn=resourceArn
            )['Tags']
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

def identify_resource_type(protectionId):
    print ("####################################################################################")
    response = {}
    try:
        shieldProtection = shield_client.describe_protection(
          ProtectionId =protectionId)['Protection']
    except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error'])
        response['Error'] = error.response['Error']
        return (response)
    resourceArn = shieldProtection['ResourceArn']
    resourceType = resourceArn.split(':')[2]
    region = resourceArn.split(":")[3]
    accountId = resourceArn.split(":")[4]
    #Resource name is Cloudfront already, no extra logic needed
    #Only possible way an ELBv2 will have a shield protection as the direct resource is an ALB
    if resourceType == 'cloudfront':
        print ("Found CloudFront!")
    if resourceType == 'globalaccelerator':
        print ("Found GlobalAccelerator!")
    elif resourceType == 'elasticloadbalancing':
        resourceType = 'alb'
    #If it is an EIP, it is either associate to an NLB, Instance or not applicable
    elif resourceType == 'ec2':
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
                resourceType = 'nlb'
                shieldProtection['ResourceArn'] = elbv2_client.describe_load_balancers(
                    Names=[
                        eniDescription.split('/')[1],
                    ])['LoadBalancers'][0]['LoadBalancerArn']
            elif "InstanceId" in address.keys():
                print ("Found Instance!")
                resourceType = "instance"
    shieldProtection['ResourceType'] = resourceType
    return (shieldProtection)
