from datetime import datetime

import boto3
import os
import copy
import json

wafv2_client =  boto3.client('wafv2')
fms_client = boto3.client('fms')

rgTemplate = {
  "AWSTemplateFormatVersion": "2010-09-09",
  "Resources": {}
}

def export_from_fms_policy(policyId):
    foundRuleGroups = []
    #Get the security policy
    policyDetails = fms_client.get_policy(PolicyId=policyId)
    policyName = policyDetails['Policy']['PolicyName']
    #Specifically get ManagedServiceData
    msd = json.loads(policyDetails['Policy']['SecurityServicePolicyData']['ManagedServiceData'])
    preProcessedRuleGroups = msd['preProcessRuleGroups']
    postProcessRuleGroups = msd['postProcessRuleGroups']
    #Check pre and post rules
    for ruleGroups in [preProcessedRuleGroups, postProcessRuleGroups]:
        for rg in ruleGroups:
            #For managed rules, replace the value at ARN with the scope and name of the rule, the fms policy generator will reverse this for the actual rule groups in place
            if rg['managedRuleGroupIdentifier'] == None:
                #print ("found custom rule group")
                rga = copy.deepcopy(rg['ruleGroupArn'])
                rgScope = rga.split(":")[-1].split("/")[0]
                rgName = rga.split(":")[-1].split("/")[2]
                rg['ruleGroupArn'] = [rgScope,rgName]
                #track the ARN of all custom rule groups references
                foundRuleGroups.append(copy.deepcopy(rga))
    msd['redactedFields'] = msd['loggingConfiguration']['redactedFields']
    #Remove elements that are not part of CLoudFormation managed service data; i.e. done elsewere
    for k in list(msd.keys()):
        if k not in ['preProcessRuleGroups','postProcessRuleGroups','redactedFields']:
            del msd[k]
    #Adjustments from raw get_rule_group to CloudFormation format and element requirements.
    if foundRuleGroups != []:
        for rg in foundRuleGroups:
            rgResponse = wafv2_client.get_rule_group(
                ARN=rg
            )['RuleGroup']
            #Remove items that are not used with CloudFormation
            for d in ['Id','ARN','LabelNamespace','AvailableLabels']:
                if d in rgResponse:
                    del rgResponse[d]
            #Check under scope down for rate limit and straight up bytematchstatement for bytes and convert to string (this is what CloudFormation wants anyways)
            for r in rgResponse['Rules']:
                if 'RateBasedStatement' in r['Statement']:
                    if 'ScopeDownStatement' in r['Statement']['RateBasedStatement']:
                        if 'ByteMatchStatement' in r['Statement']['RateBasedStatement']['ScopeDownStatement']:
                            if 'SearchString' in r['Statement']['RateBasedStatement']['ScopeDownStatement']['ByteMatchStatement']:
                                r['Statement']['RateBasedStatement']['ScopeDownStatement']['ByteMatchStatement']['SearchString'] = r['Statement']['RateBasedStatement']['ScopeDownStatement']['ByteMatchStatement']['SearchString'].decode("utf8")
                if 'ByteMatchStatement' in r['Statement']:
                    r['Statement']['ByteMatchStatement']['SearchString'] = r['Statement']['ByteMatchStatement']['SearchString'].decode("utf8")
            print (json.dumps(rgResponse))
            #Build cloudformation resources as resources in basic template
            cfnLogicalName = rgResponse['Name'].replace('-','').replace('_','')
            rgTemplate['Resources'][copy.deepcopy(cfnLogicalName)] = {
                    "Type": "AWS::WAFv2::RuleGroup",
                    "Properties": rgResponse
                }
    #Create directory with policy name if it doesn't exist
    if not os.path.exists(policyName):
        os.makedirs(policyName)

    policyFileName = policyName + "/securitypolicy-" + policyName + "-" + datetime.now().strftime("%Y-%m-%d-%H") + ".json"
    print ("Created files")
    print (policyFileName)
    #Write security policy managed service data config file
    with open(policyFileName, 'w') as policyOutFile:
        json.dump(msd, policyOutFile)
    if foundRuleGroups != []:
        rgFileName = policyName + "/wafv2-rule-groups-" + datetime.now().strftime("%Y-%m-%d-%H") + ".json"
        #If relevant, write cloudformation template to file.
        with open(rgFileName, 'w') as rgOutFile:
            json.dump(rgTemplate, rgOutFile)
        print ("Custom Rule Groups detected, CloudFormation created to deploy these as well")
        print (rgFileName)
