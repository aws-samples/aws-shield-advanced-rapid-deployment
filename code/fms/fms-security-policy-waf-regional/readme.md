## Overview
Create a Firewall Manager Security policy for AWS WAF for regional Resources
_____

## CloudFormation Details
__Template__: `code/fms/fms-security-policy-waf-regional/cfn/fms-security-policy-waf-regional.yaml`  
__Mechanism__: `CloudFormation StackSet`  
__Location(s)__: `Firewall Manager delegated administrator`  
__Region(s)__: `All Regions`

_____
## How it works

#### Native CloudFormation
Firewall Manager Security Policy except for JSON value for ManagedServiceData

#### Custom Lambda backed
A separately deployed lambda function accepts an S3Key and retrieves a JSON object from the code S3 bucket.  Lambda transforms this JSON, implementing the appropriate logging confirmation, and placeholder values for rule groups with the matching name rule group ID.  See [Easy WAF Security Policy](../../easy_waf_security_policy.md)

_____

## Dependencies:

[Self Managed Stack Sets](../../prerequisites.md)  
[Firewall Manager](../../prerequisites.md)  

[fms-policy-waf-generator module](../fms/fms-policy-waf-generator/readme.md)  

_____

## Parameter details:

#### AutoRemediate
If Security Policy should protect out of compliance resources  
__Required:__: No  
__Type__: Boolean  
__Default__: `True`  
&nbsp;  
#### ScopeType
Scope of security Policy, default is Org but can also specify Accounts or OU and provide list in relevant parameter  
__Required__: No  
__Type__: String  
__Default__: `Org`  
__AllowedValues__:
* `Org`
* `Account`  
* `OU`  

#### AccountScopeList
Comma separated list of AWS accounts to scope this Security Policy.  Only used if ScopeType is "Accounts"  
__Required__: No  
__Type__: List<String>
&nbsp;  
#### OUScopeList
Comma separated list of Organization OUs to scope this Security Policy.  Only used if ScopeType is "OU"  
__Required__: No  
__Type__: List<String>
&nbsp;  
#### IncludeExcludeScope
If list of accounts or OUs is what to include or exclude from scope.  Only functional if ScopeType is not "Org"  
__Required__: No  
__Type__: String  
__Default__: `Include`  
__AllowedValues__:  
* `Include`
* `Exclude`  

#### ResourceTagUsage
If scope tags and/or values are specified, are these tags to scope in scope or out of scope  
__Required__: No  
__Type__: String  
__Default__: `Include`  
__AllowedValues__:
* `Include`
* `Exclude`

#### OverrideCustomerWebACL
Should this SecurityPolicy replace any associated WebACL's on scoped resources  
__Required:__: No  
__Type__: Boolean  
__Default__: `False`  
&nbsp;  
#### WAFRuleKey
S3 Key to retrieve ManagedSecurityData  
__Required__: No  
__Type__: String  
__Default__: `code/fms/fms-policy-waf-generator/policy-examples/default.json`  
&nbsp;  
#### DefaultAction
WAF WebACL Default Action  
__Required__: No  
__Type__: String  
__Default__: `Allow`  
__AllowedValue__:  
* `Allow`
* `Block`  

#### WebACLResourceTypes
What type of support resource(s) should this policy protect.  Use one of the values below exactly  
__Required__: No  
__Type__: String  
__Default__: `AWS::ApiGateway::Stage,AWS::ElasticLoadBalancingV2::LoadBalancer`  
__AllowedValue__:
* `AWS::ApiGateway::Stage,AWS::ElasticLoadBalancingV2::LoadBalancer`  
* `AWS::ElasticLoadBalancingV2::LoadBalancer`  
* `AWS::ApiGateway::Stage`  
*  `<na>`  

#### PolicyName
Cosmetic Name of Security Policy  
__Required__: No  
__Type__: String  
__Default__: `CloudFrontDefaultWAFPolicy`  
&nbsp;  
#### ScopeTagName1
Value of KeyName to scope security policy  
__Required__: No  
__Type__: String
&nbsp;  
#### ScopeTagValue1
Value of KeyName to scope security policy  
__Required__: Conditional (If ScopeTagName1 is specified then yes)  
__Type__: String
&nbsp;  
#### ScopeTagName2
Value of KeyName to scope security policy  
__Required__: No  
__Type__: String
&nbsp;  
#### ScopeTagValue2
Value of KeyName to scope security policy  
__Required__: Conditional (If ScopeTagName2 is specified then yes)  
__Type__: String
&nbsp;  
#### ScopeTagName3
Value of KeyName to scope security policy  
__Required__: No  
__Type__: String
&nbsp;  
#### ScopeTagValue3
Value of KeyName to scope security policy  
__Required__: Conditional (If ScopeTagName3 is specified then yes)  
__Type__: String

_____

## Deployment Scripts
### Create Stack Set
```
aws cloudformation create-stack-set \
--stack-set-name fms-security-policy-waf-regional \
--template-body file://code/fms/fms-security-policy-waf-regional/cfn/fms-security-policy-waf-regional.yaml \
--capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM CAPABILITY_IAM \
--permission-model SELF_MANAGED \
--execution-role-name AWSCloudFormationStackSetExecutionRole \
--administration-role-arn arn:aws:iam::$PayerAccountId:role/AWSCloudFormationStackSetAdministrationRole \
--parameters \
ParameterKey=PolicyName,ParameterValue=cloudfrontpolicydefault \
ParameterKey=AutoRemediate,ParameterValue=true \
ParameterKey=WAFRuleKey,ParameterValue=code/fms/fms-policy-waf-generator/policy-examples/default.json
```

### Add stacks to stackset
```
aws cloudformation create-stack-instances \
--stack-set-name fms-security-policy-waf-regional \
--regions us-east-1 \
--deployment-targets Accounts=$FMSAccountId
```
