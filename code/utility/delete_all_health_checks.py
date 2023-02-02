#Helper script to delete all health check templates.  This is the easiest way to force template updates to all health check templates or otherwise delete health checks at scale.  Note, this deletes any existing and stable CloudFormation stack that has a name that begins with "HealthCheck-"

import boto3
#Update to list all regions you deployed into
regions = ['us-east-1','us-east-2']
for region in regions:
    cf_client = boto3.client('cloudformation',region_name=region)
    list_stacks_paginator = cf_client.get_paginator('list_stacks')
    stacks = list_stacks_paginator.paginate().build_full_result()['StackSummaries']

    for stack in stacks:
        if stack['StackName'].startswith('HealthChecks-') and stack['StackStatus'].endswith('COMPLETE') and stack['StackStatus'] != "DELETE_COMPLETE":
            print (stack['StackName'] + " Deleting!")
            response = cf_client.delete_stack(
                StackName=stack['StackName'])
