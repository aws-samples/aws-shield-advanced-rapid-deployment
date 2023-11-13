import boto3, time


#UPDATE
try:
    available_profiles = [
        'dev'
    ]
    available_regions = [
        'us-east-1',
        'eu-west-1',
        'us-west-2',
        'ca-central-1',
        'ap-northeast-1',
        'ap-southeast-1',
        'ap-southeast-2',
    ]
    StackStatusFilterS=[
        'DELETE_FAILED',
        # 'CREATE_COMPLETE',
        # 'UPDATE_COMPLETE',
    ]
    FailCount = []
    while(1):
        print(len(FailCount))
        time.sleep(5)
        for profile in available_profiles:
            for region in available_regions:
                aws_session = boto3.session.Session(profile_name=profile, region_name=region)
                cloudformation = aws_session.client('cloudformation')
                response = cloudformation.list_stacks(
                    StackStatusFilter=StackStatusFilterS
                )
                for stack in response.get('StackSummaries'):
                    failedStack = (stack.get('StackName'))
                    FailCount.append(failedStack)
                    print(f'Deletion Failed for {failedStack} in Account {profile} and Region {region}')
except Exception as e:
    print(f'An error occurred: {e}')