import sys
import boto3
ssm_client = boto3.client('ssm')
fms_client = boto3.client('fms')
userId = sys.argv[1]
#fms-ssm-test-10
policies = fms_client.list_policies()['PolicyList']
createNew = True
managedServiceData = ""
for policy in policies:
    if policy['PolicyName'] == userId:
        managedServiceData = fms_client.get_policy(PolicyId=policy['PolicyId'])['Policy']['SecurityServicePolicyData']['ManagedServiceData']
    elif policy['PolicyName'] == (userId + "builder"):
        createNew = False
if managedServiceData == "":
    print ("No Security policy found with that name")
elif createNew:
    fms_client.put_policy(
        Policy={
            'PolicyName': userId + "builder",
            'SecurityServicePolicyData': {
                'Type': 'WAFV2',
                'ManagedServiceData': managedServiceData
            },
            'ResourceType': 'AWS::CloudFront::Distribution',
            'ExcludeResourceTags': False,
            'RemediationEnabled': False,
            'ResourceTags': [
                {
                    'Key': 'foo',
                    'Value': 'foo'
                },
                {
                    'Key': 'foo',
                    'Value': 'bar'
                },
    
            ]
    	},
    	TagList=[
            {
                'Key': 'UserId',
                'Value': userId
            }
        ]
    )
else:
    print ("Policy: " + userId + "builder already exists")