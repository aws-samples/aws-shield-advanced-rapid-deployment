## Overview
Creates a delivery stream

_____

## CloudFormation Details
__Template__: `kinesis/kinesis-firehost-delivery-stream/cfn/kinesis-firehose-delivery-stream.yaml`  
__Mechanism__: `CloudFormation StackSet`  
__Location(s)__: `Firewall Manager Administrator Account`  
__Region(s)__: `All Region`

_____

## How it works

#### Native CloudFormation
Kinesis Firehose, IAM Role, Default KMS Alias & Key (If existing key not provided)

_____

## Dependencies

* [Self Managed Stack Sets](../../prerequisites.md)  
_____

## Parameter details

#### ProductName  
Cosmetic name used to construct resource names.  When deploying this multiple times, specific a different product to avoid name collision and isolation of stack resources  
__Required:__: No  
__Type__: String  


#### WafLogsS3Bucket  
Full S3 bucket name were WAF logs are stored  
__Required__: Yes  
__Type__: String  
&nbsp;  
#### WafLogsS3Prefix  
S3 root prefix where WAF logs should be store.  Do NOT include account ID/region as  WAF automatically includes this  
__Required__: No  
__Type__: String  
__Default__: /  
&nbsp;  
#### SourceIPAddressSource  
How to determine the true source IP of requestors in logs.  SOURCE_IP (Default) is the TCP source IP seen by WAF.  Any other value will treat this value as a header name and use the value of this header as the source IP (e.g. X-FORWARDED-FOR)  
__Required__: No  
__Type__: String  
__Default__: SOURCE_IP  

_____
## Deployment Scripts
### Create Stack Set
```
aws cloudformation create-stack-set \
--stack-set-name kinesis-firehose-delivery-stream \
--template-body file://code/kinesis/kinesis-firehose-delivery-stream/cfn/kinesis-firehose-delivery-stream.yaml \
--capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM CAPABILITY_IAM \
--permission-model SELF_MANAGED \
--execution-role-name AWSCloudFormationStackSetExecutionRole \
--administration-role-arn arn:aws:iam::$PayerAccountId:role/AWSCloudFormationStackSetAdministrationRole \
--parameters \
ParameterKey=WAFLogS3Bucket,ParameterValue=central-waf-logs-$PayerAccountId-$PrimaryRegion
```

### Add stacks to stackset
```
aws cloudformation create-stack-instances \
--stack-set-name kinesis-firehose-delivery-stream \
--regions $Regions \
--deployment-targets Accounts=$FMSAccountId
```
