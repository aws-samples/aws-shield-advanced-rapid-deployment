import boto3
import time


# UPDATE
try:
    profile = "admin"
    available_regions = [
        'us-east-1',
        'eu-west-1',
        'us-west-2',
        'ca-central-1',
        'ap-northeast-1',
        'ap-southeast-1',
        'ap-southeast-2',
    ]


    for region in available_regions:
        aws_session = boto3.session.Session(profile_name=profile, region_name=region)
        fms = aws_session.client('fms')
        PoliciesinRegion = fms.list_policies(
        )
        print("-----")
        ListOfPolicies = PoliciesinRegion.get('PolicyList')
        if PoliciesinRegion.get('NextToken') != None:
            # print(PoliciesinRegion.get('NextToken'))
            PoliciesinRegion = fms.list_policies(
            NextToken = PoliciesinRegion.get('NextToken'))
            ListOfPolicies.append(PoliciesinRegion.get('PolicyList'))
            # print(ListOfPolicies)
        
        for policies in ListOfPolicies:
            # print(policies)
            if type(policies) != list:
                if "WAFPolicy" in policies.get('PolicyName'):
                    print("Deleting Policy")
                    print(policies.get('PolicyName'))    
                    fms.delete_policy(
                        PolicyId=policies.get('PolicyId'),
                        DeleteAllPolicyResources=True
                    )
except Exception as e:
    print(f"An error occurred: {e}")