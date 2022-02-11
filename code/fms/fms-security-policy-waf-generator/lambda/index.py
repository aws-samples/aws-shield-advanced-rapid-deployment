import sys
sys.path.insert(0,'./fms/fms-policy-waf-generator/lambda')

import json
import botocore
import cfnresponse
import boto3
import os
client = boto3.client('s3')
accountId = os.environ['AccountId']
region = os.environ['Region']
wafv2_client = boto3.client('wafv2')
ssm_client = boto3.client('ssm')
codeS3BucketPrefix = os.environ['CodeS3BucketPrefix']

globalRuleGroups = {}
regionalRuleGroups = {}
if region == 'us-east-1':
    globalResponse = wafv2_client.list_rule_groups(Scope='CLOUDFRONT')['RuleGroups']
    for r in globalResponse:
      globalRuleGroups[r['Name']] = r['Id']
    print ("globalRuleGroups")
    print (globalRuleGroups)
else:
    globalRuleGroups = {}

regionalResponse = wafv2_client.list_rule_groups(Scope='REGIONAL')['RuleGroups']
for r in regionalRuleGroups:
  regionalRuleGroups[r['Name']] = r['Id']
print ("regionalRuleGroups")
print (regionalRuleGroups)
def lambda_handler(event, context):
  print (event)
  if event.get('RequestType', None) == 'Delete':
    cfnresponse.send(event, context, cfnresponse.SUCCESS, dict(), 'GracefulContinue')
    return
  try:
    rProperties = event['ResourceProperties']
    #wafRuleKey = rProperties['wafRuleKey']
    overrideCustomerWebACLAssociation = rProperties['OverrideCustomerWebACLAssociation']
    defaultAction = rProperties['DefaultAction']
    ManagedServiceDataTemplate = rProperties['ManagedServiceDataTemplate']
    wafRuleData = json.loads(ssm_client.get_parameter(
        Name=ManagedServiceDataTemplate,
        WithDecryption=False
    )['Parameter']['Value'])
    print (wafRuleData)
    preProcessedRules = wafRuleData['preProcessRuleGroups']
    postProcessedRules = wafRuleData['postProcessRuleGroups']
    redactedFields = wafRuleData['loggingConfiguration']['redactedFields']
    if 'loggingFilterConfigs' in wafRuleData:
      loggingFilterConfigs = wafRuleData['loggingFilterConfigs']
    else:
      loggingFilterConfigs = None
    template = {
        "type": "WAFV2",
        "preProcessRuleGroups": [],
        "postProcessRuleGroups": [],
        "defaultAction": {
          "type": "${DefaultAction}"
        },
        "overrideCustomerWebACLAssociation": "${OverrideCustomerWebACL}",
        "loggingConfiguration": {
          "logDestinationConfigs": [
            "arn:aws:firehose:${AWS::Region}:${AWS::AccountId}:deliverystream/aws-waf-logs-delivery-${AWS::AccountId}-${AWS::Region}"
          ],
          "redactedFields": []
        }
      }

    template['preProcessRuleGroups'] = preProcessedRules

    for preRule in template['preProcessRuleGroups']:
      if 'ruleGroupArn' in preRule:
        if not preRule['ruleGroupArn'] == None:
          scope = preRule['ruleGroupArn'][0]
          name = preRule['ruleGroupArn'][1]
          print ("Scope: " + scope)
          print ("Name: " + name)
          if scope == 'global':
            if name in list(globalRuleGroups.keys()):
              preRule['ruleGroupArn'] = wafv2_client.get_rule_group(
                  Name=name,
                  Scope='CLOUDFRONT',
                  Id=globalRuleGroups[name]
              )['RuleGroup']['ARN']
            else:
              responseData = {}
              responseData['Response'] = "RuleGroupNotFound"
              cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "fsm-generate-policy")
              return ("RuleGroupNotFound")
          else:
            if name in list(regionalRuleGroups.keys()):
              preRule['ruleGroupArn'] = wafv2_client.get_rule_group(
                  Name=name,
                  Scope='REGIONAL',
                  Id=globalRuleGroups[name]
              )['RuleGroup']['ARN']
            else:
              responseData = {}
              responseData['Response'] = "RuleGroupNotFound"
              cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "fsm-generate-policy")
              return ("RuleGroupNotFound")

    template['postProcessRuleGroups'] = postProcessedRules
    for postRule in template['postProcessRuleGroups']:
        if 'ruleGroupArn' in postRule:
          if not postRule['ruleGroupArn'] == None:
            scope = postRule['ruleGroupArn'][0]
            name = postRule['ruleGroupArn'][1]
            if scope == 'global':
              if name in list(globalRuleGroups.keys()):
                postRule['ruleGroupArn'] = wafv2_client.get_rule_group(
                    Name=name,
                    Scope='CLOUDFRONT',
                    Id=regionalRuleGroups[name]
                )['RuleGroup']['ARN']
              else:
                responseData = {}
                responseData['Response'] = "RuleGroupNotFound"
                cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "fsm-generate-policy")
                print ("RuleGroupNotFound")
                return ("RuleGroupNotFound")
            else:
              if name in list(regionalRuleGroups.keys()):
                postRule['ruleGroupArn'] = wafv2_client.get_rule_group(
                    Name=name,
                    Scope='REGIONAL',
                    Id=regionalRuleGroups[name]
                )['RuleGroup']['ARN']
              else:
                responseData = {}
                responseData['Response'] = "RuleGroupNotFound"
                cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "fsm-generate-policy")
                print ("RuleGroupNotFound")
                return ("RuleGroupNotFound")

    template['defaultAction']['type'] = defaultAction
    template['overrideCustomerWebACLAssociation'] = overrideCustomerWebACLAssociation
    template['loggingConfiguration']['logDestinationConfigs'] = ["arn:aws:firehose:" + region + ":" + accountId + ":deliverystream/aws-waf-logs-delivery-" +accountId + "-" + region]
    template['loggingConfiguration']['redactedFields'] = redactedFields
    if loggingFilterConfigs:
      template['loggingConfiguration']['loggingFilterConfigs'] = loggingFilterConfigs
    print (template)
    if 'RequestType' in event:
      responseData = {}
      responseData['Template'] = json.dumps(template)
      cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "fsm-generate-policy")
    return (template)
  except botocore.exceptions.ClientError as error:
      print (error.response)
      responseData = {}
      responseData['Response'] = "FAILED"
      cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "fsm-generate-policy")
