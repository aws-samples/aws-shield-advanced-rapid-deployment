# Easy WAF Security Policy  
Native CloudFormation or CLI requires constructing a complicated JSON object representing the WAF rules for an AWS WAF security policy.  Instead, in this process, you create a security policy in the console (easier) and then export the configuration into the required format for CloudFormation to console.



##  How it works
Import the references python script and execute against a console created security policy.  The script retrieves the given security policy and transforms into a json file.  This file is read by fms-generate-security-policy to create an actual managed security data value for AWS WAF.  While itterating through the security policy, if a custom rule is detected, the script creates the CloudFormation template to deploy that security group through CloudFormation.  This provides a version controllable artifact, or can be used to deploy the actual security group (or update).



## How to use

Navigate to /utility  
Run the following python commands to import the module and run the module with the appropriate policyId in place (line 1)


```
policyId = '1234abcd'
from export_from_fms_policy import export_from_fms_policy
export_from_fms_policy(policyId)
```

[/easy_waf_security_policy](../export_from_fms_policy.py)

You will get one or two files as output under a directory with the security policy name.  
This is named: `securitypolicy-<policyName>-<yyyy-mm-dd-hh>.json`  

Below is the structure of the file:  

```
{
  "preProcessRuleGroups": [],
  "postProcessRuleGroups": [],
  "redactedFields": []
}

```

Below is an example with several Amazon managed rules:  

```
{
  "preProcessRuleGroups": [
    {
      "overrideAction": {
        "type": "COUNT"
      },
      "managedRuleGroupIdentifier": {
        "vendorName": "AWS",
        "managedRuleGroupName": "AWSManagedRulesCommonRuleSet"
      },
      "ruleGroupType": "ManagedRuleGroup",
      "excludeRules": []
    },
    {
      "overrideAction": {
        "type": "COUNT"
      },
      "managedRuleGroupIdentifier": {
        "vendorName": "AWS",
        "managedRuleGroupName": "AWSManagedRulesKnownBadInputsRuleSet"
      },
      "ruleGroupType": "ManagedRuleGroup",
      "excludeRules": []
    },
    {
      "overrideAction": {
        "type": "NONE"
      },
      "managedRuleGroupIdentifier": {
        "vendorName": "AWS",
        "managedRuleGroupName": "AWSManagedRulesAmazonIpReputationList"
      },
      "ruleGroupType": "ManagedRuleGroup",
      "excludeRules": []
    }
  ],
  "postProcessRuleGroups": [],
  "redactedFields": []
}
```

This file should be uploaded to the CodeS3Bucket in each region(s).  Note the key the file is uploaded to, you will need to provide that for fms-security-policy-waf-cloudfront and fms-seciruty-policy-waf-regional as "WAFRuleKey"
