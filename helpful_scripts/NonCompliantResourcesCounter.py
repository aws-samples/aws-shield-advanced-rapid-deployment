import boto3
import time
try:
    from botocore.config import Config
    config = Config(
       retries = {
          'max_attempts': 10,
          'mode': 'standard'
       }
    )
    
    
    #UPDATE
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
    
    stackSetNameKeyWord = "StackSet-proactive-engagement-sqs-"
    remaining_resources = []
    region_counter = 0
    account_counter = 0
    total_resources = 0
    for profile in available_profiles:
        for region in available_regions:
            aws_session = boto3.session.Session(profile_name=profile, region_name=region)
            config = aws_session.client('config')
            config_response = config.describe_config_rules()
            rulesList = config_response['ConfigRules']
            rule = next((
                e for e in rulesList if stackSetNameKeyWord in e.get('ConfigRuleName')), None)
            # print(rule)
            if rule is None:
                continue
    
            checkRule = rule.get('ConfigRuleName')
            response = config.get_compliance_details_by_config_rule(
                ConfigRuleName=checkRule,
                ComplianceTypes=[
                    'NON_COMPLIANT'
                ]
            )
            NextTokenValue = response.get('NextToken')
    
            for compliance in response.get('EvaluationResults'):
                remaining_resources.append(compliance.get('ComplianceType'))
    
            while NextTokenValue:
                response = config.get_compliance_details_by_config_rule(
                    ConfigRuleName=checkRule,
                    ComplianceTypes=[
                        'NON_COMPLIANT'
                    ],
                    NextToken=NextTokenValue
                )
                NextTokenValue = response.get('NextToken')
                for resource in response.get('EvaluationResults'):
                    remaining_resources.append(compliance.get('ComplianceType'))
    
            region_counter = len(remaining_resources)
            remaining_resources = []
            print(f'Resources left in {region} : {region_counter}')
            account_counter += region_counter
        print(f'Resources left in Account {profile} : {account_counter}')
        total_resources += account_counter
        account_counter = 0
    print(f'Total Resources left : {total_resources}')
    
except Exception as e:
    print(f"An error occurred: {e}")