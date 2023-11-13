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
    
    RegionsList = [
        "us-east-1", 
        "us-west-2", 
        "ca-central-1", 
        "eu-west-1", 
        "ap-northeast-1", 
        "ap-southeast-1", 
        "ap-southeast-2"
    ] 
    
    StackSetKeyWordInclude = "HealthCheck" 
    StackSetKeyWordExclude1 = 'FirewallManager'
    StackSetKeyWordExclude2 = "StackSet" 
    StackSetKeyWordExclude3 = "ProactiveEngagement"
    
    StackStatusFilterS=[
        'DELETE_FAILED',
        # 'CREATE_COMPLETE',
        # 'UPDATE_COMPLETE',
    ]
    
    #UPDATE ENDS
    
    #Variables
    AttemptCount = 1
    DeletionCounter = 1
    all_stacks = list()
    failed_healtchecks = list()
    #Variables ENDS
    
    #Functions
    def isMultipleof50(n):  
        while ( n > 0 ):
            n = n - 50
        if ( n == 0 ):
            return 1
        return 0
    
    def SurfRegions2Delete(profile,available_regions,StackSetKeyWordInclude,StackSetKeyWordExclude1,StackSetKeyWordExclude2,StackSetKeyWordExclude3):
        print(profile)
        for region in available_regions:
            print(region)
            aws_session = boto3.session.Session(profile_name=profile, region_name=region)
            client = aws_session.client('cloudformation')
            client_route53 = aws_session.client('route53')
            response = client.list_stacks(
                StackStatusFilter=StackStatusFilterS
            )
            all_stacks_response = response.get('StackSummaries')
    
            while 'NextToken' in response:
                response = client.list_stacks(
                    StackStatusFilter=StackStatusFilterS,
                    NextToken=response.get('NextToken')
                )
                all_stacks_response.extend(response.get('StackSummaries'))
    
            print(len(all_stacks_response))
            for stack in all_stacks_response:
                DeletionCounter =+ 1
                
                if StackSetKeyWordInclude in stack.get('StackName') and StackSetKeyWordExclude1 not in stack.get('StackName') \
                    and StackSetKeyWordExclude2 not in stack.get('StackName') and StackSetKeyWordExclude3 not in stack.get('StackName'):
                    failedStack = (stack.get('StackName'))
                    resources = client.list_stack_resources(
                        StackName=failedStack
                    )
                    print(f'failed stack: {failedStack}')
                    try:
                        print('delete hc')
                        for hc in [e.get('PhysicalResourceId') for e in 
                        resources.get('StackResourceSummaries') if 'HealthCheck' in e.get('ResourceType') 
                                        and e.get('ResourceStatus')=='DELETE_FAILED']:
                            response = client_route53.delete_health_check(
                                HealthCheckId=hc
                            )
                    except Exception as e:
                        print(e)
                        if 'still referenced from parent health check' in str(e):
                            hc_id = str(e).split(' ')[-1]
                            response = client_route53.delete_health_check(
                                    HealthCheckId=hc_id
                                )
                    if next((e for e in resources.get('StackResourceSummaries') if 'ShieldProtectionHealthCheck' in e.get('ResourceType') 
                    and e.get('ResourceStatus') in ["DELETE_FAILED", "DELETE_SKIPPED"]), None) is not None:
                        delete_response = client.delete_stack(
                        StackName=failedStack,
                        RetainResources=[ 'ShieldAssociation']
                        )
                    elif next((e for e in resources.get('StackResourceSummaries') if 'ShieldProtectionHealthCheck' in e.get('ResourceType') 
                    and e.get('ResourceStatus') != "DELETE_IN_PROGRESS"), None) is not None:
                        delete_response = client.delete_stack(
                        StackName=failedStack
                        )
                    elif next((e for e in resources.get('StackResourceSummaries') if 'ShieldProtectionHealthCheck' in e.get('ResourceType')), None) is None:
                        print('No Shield Protection')
                        delete_response = client.delete_stack(
                        StackName=failedStack
                        )
                    all_stacks.append(failedStack)
                    # print('{profile}|{region}|{failedStack}')
                DeletionCounter =+ 1
                
                if isMultipleof50(DeletionCounter):
                    time.sleep(10)
                else:
                    time.sleep(1)
                
    #Functions End
    
    #Logic Execution Starts
    for profile in available_profiles:
        # SurfRegions2Delete(profile,available_regions,StackSetKeyWordInclude,StackSetKeyWordExclude1,StackSetKeyWordExclude2,StackSetKeyWordExclude3)
        while AttemptCount < 7:
            SurfRegions2Delete(profile,available_regions,StackSetKeyWordInclude,StackSetKeyWordExclude1,StackSetKeyWordExclude2,StackSetKeyWordExclude3)
            AttemptCount += 1
            time.sleep(30)
    #Logic Execution Ends
    
except Exception as e:
    print(f"An error occurred: {e}")