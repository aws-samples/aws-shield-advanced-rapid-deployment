import boto3
import json
import copy
import logging
import botocore
import os

logger = logging.getLogger('WAFRuleInjection')
logger.setLevel('DEBUG')

waf_client = boto3.client('wafv2')
s3_client = boto3.client('s3')

def update_waf_rule(wName, wId, wScope):
    logger.info("Evaluating: " + wName + " | " + wId + " | " + wScope)
    rateBasedRuleAction = os.environ['RateBasedRuleAction']
    rateBasedRuleValue = int(os.environ['RateBasedRuleValue'])
    rateBaseAggregateKey = os.environ['RateBaseAggregateKey']
    rateBaseAggregateKeyHeaderName = os.environ['RateBaseAggregateKeyHeaderName']
    rateBaseAggregateKeyFallback = os.environ['RateBaseAggregateKeyFallback']
    snsTopicDetails = os.environ['snsTopicDetails']
    snsaccountID = snsTopicDetails.split("|")[0]
    snsTopicName = snsTopicDetails.split("|")[1]
    wafRuleKey = os.environ['WAFRuleKey']
    codeS3Bucket = os.environ['CodeS3Bucket']
    snsTopicArn = ":".join(["arn:aws:sns",os.environ['AWS_REGION'],snsaccountID, snsTopicName])
    webACLPolicyIdentifier = os.environ['WebACLPolicyIdentifier']
    rbrName = os.environ['RBRName']
    #Only evaluate when the WebACL Name contains the string indentifier webACLPolicyIdentifier
    if webACLPolicyIdentifier not in wName:
        logger.info ("WebACL identifier did not match, no action")
        return ("WebACL identifier did not match, no action")
    else:
        try:
            acl = waf_client.get_web_acl(
                Name=wName,
                Scope=wScope,
                Id=wId
            )
            lockToken =  acl['LockToken']
            acl = acl['WebACL']
            #We will update as needed this list of rules
            rules = copy.deepcopy(acl['Rules'])
            #Copy of rules before modifications.  Used to validate if anything actually changed and we should update the WebACL
            initialRules = copy.deepcopy(rules)
        except botocore.exceptions.ClientError as error:
            logger.error(error.response['Error']['Message'])
            return ()
        #If wafRuleKey is not defined, construct a rate based rule based on parameters
        if wafRuleKey == "<na>":
            logger.info("Build rate based rule with CFN Parameters")
            #Rate Based Rule Framework
            rateRuleTemplate = {
                'Name': rbrName, 
                'Priority': 1,
                'Statement': {
                    'RateBasedStatement': {
                        'Limit': rateBasedRuleValue,
                        'AggregateKeyType': rateBaseAggregateKey
                        }
                    },
                    'Action': {
                        'Block': {}
                        
                    },
                    'VisibilityConfig': {
                        'SampledRequestsEnabled': True,
                        'CloudWatchMetricsEnabled': True,
                        'MetricName': 'RateBasedLimit'
                        }
                    }
            if rateBaseAggregateKey == "FORWARDED_IP":
                rateRuleTemplate['Statement']['RateBasedStatement']['ForwardedIPConfig'] = {'HeaderName': rateBaseAggregateKeyHeaderName, 'FallbackBehavior': rateBaseAggregateKeyFallback}
            if rateBasedRuleAction == 'Block':
                rateRuleTemplate['Action'] = {'Block': {}}
            elif rateBasedRuleAction == 'Count':
                rateRuleTemplate['Action'] = {'Count': {}}
            else:
                return ("Invalid Rule Action provided")
            logger.debug("TemplateBuildRule")
            logger.debug(rateRuleTemplate)
            highestPriorityRule = 0
            #If we are injecting a new rule and not updating an existing rule, we place the new rule last in local rules
            foundRule = False
            #UpdateExistingRateBasedRuleIfFound
            for key, rule in enumerate(rules):
                if rules[key]['Name'] == rbrName:
                    logger.debug("Existing Rule Found, updating that rule")
                    foundRule = True
                    rateRuleTemplate['Priority'] = copy.deepcopy(rules[key]['Priority'])
                    rules[key] = rateRuleTemplate
            if foundRule == False:
                logger.debug("No Rule Found, adding to end of current rule list")
                for rule in rules:
                    logger.debug("currentHighest" + str(highestPriorityRule))
                    logger.debug(rule['Priority'])
                    if rule['Priority'] > highestPriorityRule:
                        highestPriorityRule = rule['Priority']
                logger.debug("Priority")
                logger.debug(highestPriorityRule + 1)
                rateRuleTemplate['Priority'] = highestPriorityRule + 1
                rules.append(rateRuleTemplate)
            logger.debug (rules)
        #Add JSON List of Rules to WebACL, this is most appropiate for more complex rule injection that are not supported by AWS Firewall Manager
        else:
            logger.info("Add rule from S3 JSON List")
            try:
                s3Response = s3_client.get_object(
                    Bucket=codeS3Bucket,
                    Key=wafRuleKey)['Body']
                injectRules = json.loads(s3Response.read().decode("utf-8"))
                #Look for rules with a name matching the injection list of rules, update those rules if we find a match
                injectList = copy.deepcopy(injectRules)
                for iRule in injectList:
                    for rule in rules:
                        if rule['Name'] == iRule['Name']:
                            rule = copy.deepcopy(iRule)
                            injectRules.remove(iRule)
                #If anything is left over, append that as it is a new rules
                for iRule in injectRules:
                    rules.append(iRule)
            except botocore.exceptions.ClientError as error:
                logger.error(error.response['Error']['Message'])
                return (error.response['Error']['Message'])        
        try:
            if not initialRules == rules:
                logger.info("Rule change(s) detected.  Updating WebACL")
                response = waf_client.update_web_acl(
                    Name=wName,
                    Scope=wScope,
                    Id=wId,
                    DefaultAction=acl['DefaultAction'],
                    Rules=rules,
                    VisibilityConfig=acl['VisibilityConfig'],
                    LockToken=lockToken
                )
                logger.debug(response)
            else:
                logger.info("Rules did not change.  No need to update WebACL")
        except botocore.exceptions.ClientError as error:
            logger.error(error.response['Error']['Message'])
            return (error.response['Error']['Message'])        
    
