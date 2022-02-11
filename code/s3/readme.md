## Overview
Creates a S3 bucket with access policy for inbound WAF logs and logging bucket for S3 access logs (if not provided)

_____

## CloudFormation Details
__Template__: `code/s3/s3-bucket-waf-logs.yaml`  
__Mechanism__: `CloudFormation Stack`  
__Location(s)__: `Firewall Manager delegated administrator`  
__Region(s)__: `Primary Region (us-east-1)`

_____
## How it works
#### Native CloudFormation
Native CloudFormation.  No need to reinvent the wheel!

_____

## Dependencies

* Account subscribed to Shield Advanced Subscribed  
* [Self Managed Stack Sets](../../prerequisites.md)  

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

&nbsp;  
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

&nbsp;  
#### ResourceTagUsage
If scope tags and/or values are specified, are these tags to scope in scope or out of scope  
__Required__: No  
__Type__: String  
__Default__: `Include`  
__AllowedValues__:
* `Include`  
* `Exclude`  

&nbsp;  
#### OverrideCustomerWebACL
Should this SecurityPolicy replace any associated WebACL's on scoped resources  
__Required:__: No  
__Type__: Boolean  
__Default__: `False`

&nbsp;  
#### ScopeTagName1
Value of KeyName to scope security policy.  
__Required__: No  
__Type__: String

&nbsp;  
#### ScopeTagValue1
Value of KeyName to scope security policy.  
__Required__: Conditional `(If ScopeTagName1 is specified then yes)`  
__Type__: String

&nbsp;  
#### ScopeTagName2
Value of KeyName to scope security policy.  
__Required__: No  
__Type__: String

&nbsp;  
#### ScopeTagValue2
Value of KeyName to scope security policy.  
__Required__: Conditional `(If ScopeTagName2 is specified then yes)`  
__Type__: String

&nbsp;  
#### ScopeTagName3
Value of KeyName to scope security policy.  
__Required__: No  
__Type__: String

&nbsp;  
#### ScopeTagValue3
Value of KeyName to scope security policy.  
__Required__: Conditional `(If ScopeTagName3 is specified then yes)`  
__Type__: String

_____


## Deployment scripts
### Create stack:
```
aws cloudformation create-stack --stack-name s3-bucket-waf-logs \
--template-body file://code/s3/cfn/s3-bucket-waf-logs.yaml \
--capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM CAPABILITY_IAM \
--parameters \
ParameterKey=AWSOrgId,ParameterValue=$OrgId
```
