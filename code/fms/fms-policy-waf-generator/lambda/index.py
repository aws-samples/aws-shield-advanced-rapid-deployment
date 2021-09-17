import sys
sys.path.insert(0,'./fms/lambda/fms-policy-generator')

import json
import cfnresponse
import boto3
import os
client = boto3.client('s3')
accountId = os.environ['AccountId']
region = os.environ['Region']
codeS3BucketPrefix = os.environ['CodeS3BucketPrefix']
def lambda_handler(event, context):
  print (event)
  try:
    rProperties = event['ResourceProperties']
    wafRuleKey = rProperties['wafRuleKey']
    overrideCustomerWebACLAssociation = rProperties['OverrideCustomerWebACLAssociation']
    defaultAction = rProperties['DefaultAction']
    s3Body = client.get_object(
        Bucket=codeS3BucketPrefix + "-" + region,
        Key=wafRuleKey)['Body']
    wafRuleData = json.loads(s3Body.read().decode("utf-8"))
    preProcessedRules = wafRuleData['preProcessRuleGroups']
    postProcessedRules = wafRuleData['postProcessRuleGroups']
    redactedFields = wafRuleData['redactedFields']
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
    template['postProcessRuleGroups'] = postProcessedRules
    template['defaultAction']['type'] = defaultAction
    template['overrideCustomerWebACLAssociation'] = overrideCustomerWebACLAssociation
    template['loggingConfiguration']['logDestinationConfigs'] = ["arn:aws:firehose:" + region + ":" + accountId + ":deliverystream/aws-waf-logs-delivery-" +accountId + "-" + region]
    template['loggingConfiguration']['redactedFields'] = redactedFields
    print (template)
    if 'RequestType' in event:
      responseData = {}
      responseData['Template'] = json.dumps(template)
      cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "fsm-generate-policy")
    return (template)
  except:
      responseData = {}
      responseData['Response'] = "FAILED"
      cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "fsm-generate-policy")