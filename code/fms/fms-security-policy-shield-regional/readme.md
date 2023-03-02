## Overview
Create a Firewall Manager Security policy to enable Shield Advanced protection to Regional resources.

_____

## CloudFormation Details
__Run in__: `AWS Organizational MGMT/Administrator Account`
__Mechanism__: `CloudFormation StackSet`  
__Template__: `code/fms/fms-security-policy-shield-regional/cfn/fms-security-policy-shield-regional.yaml`  
__Deploy to__: `Firewall Manager delegated administrator`  
__Region(s)__: `regions specified within the “environment_variables.sh” file`

_____
## How it works
#### Native CloudFormation
Native CloudFormation.  No need to reinvent the wheel!

_____

## Dependencies

* Account subscribed to Shield Advanced Subscribed  
* [Service Managed Stack Sets](../../prerequisites.md)  
* [AWS Firewall Manager](../../prerequisites.md)  

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
#### ProtectRegionalResourceTypes
What type of support resource(s) should this policy protect.  Use one of the values below exactly  

__Required__: No  
__Type__: String  
__AllowedValues__:
* `AWS::ElasticLoadBalancingV2::LoadBalancer,AWS::ElasticLoadBalancing::LoadBalancer,AWS::EC2::EIP`  
* `AWS::ElasticLoadBalancingV2::LoadBalancer,AWS::ElasticLoadBalancing::LoadBalancer`  
* `AWS::ElasticLoadBalancingV2::LoadBalancer,AWS::EC2::EIP`  
* `AWS::ElasticLoadBalancing::LoadBalancer,AWS::EC2::EIP`  
* `AWS::ElasticLoadBalancingV2::LoadBalancer`  
* `AWS::ElasticLoadBalancing::LoadBalancer`  
* `AWS::EC2::EIP`

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
### Create stack set
```
aws cloudformation create-stack-set \
--stack-set-name fms-security-policy-shield-regional \
--template-body file://code/fms/fms-security-policy-shield-regional/cfn/fms-security-policy-shield-regional.yaml \
--capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM CAPABILITY_IAM \
--permission-model SELF_MANAGED \
--execution-role-name AWSCloudFormationStackSetExecutionRole \
--administration-role-arn arn:aws:iam::$PayerAccountId:role/AWSCloudFormationStackSetAdministrationRole \
--parameters \
ParameterKey=ScopeType,ParameterValue=Org \
ParameterKey=ProtectRegionalResourceTypes,ParameterValue=AWS::ElasticLoadBalancingV2::LoadBalancer,AWS::ElasticLoadBalancing::LoadBalancer,AWS::EC2::EIP \
ParameterKey=IncludeExcludeScope,ParameterValue=Include \
ParameterKey=AutoRemediate,ParameterValue=True \
ParameterKey=ScopeType,ParameterValue=Org \
ParameterKey=ResourceTagUsage,ParameterValue=Include

```

### Add stacks to stackset
```
aws cloudformation create-stack-instances \
--stack-set-name fms-security-policy-shield-regional \
--regions $Regions \
--deployment-targets Accounts=$FMSAccountId
```
