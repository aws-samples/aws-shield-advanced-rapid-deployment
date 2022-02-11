## Overview
WAF implementation and operation requires the ability to quickly understand WAF logs.  This creates a dedicated Athena Workgroup with the required tables and a number of queries to simplify WAF log data into a more human consumable format and helps evaluate logs for a number of common use cases.

_____

## CloudFormation Details
__Template__: `athena/cfn/athena-workgroup-views.yaml`  
__Mechanism__: `CloudFormation Stack`  
__Location(s)__: `Firewall Manager Administrator Account`  
__Region(s)__: `Primary Region (us-east-1)`  

_____

## How it works

#### Native CloudFormation
Athena Workgroup, Athena/Glue database/tables, named queries

#### Custom Lambda backed
Athena views (from named queries)

_____

## Dependencies

_____

## Parameter details

#### ProductName  
Cosmetic name used to construct resource names.  When deploying this multiple times, specific a different value to avoid name collision and isolation of stack resources.  
__Required:__: No  
__Type__: String  

#### WafLogsS3Bucket  
Full S3 bucket name were WAF logs are stored  
__Required__: Yes  
__Type__: String  

#### WafLogsS3Prefix  
Either / if no prefix or the prefix ending with / for WAF logs stored in S3.  This should NOT include account ID/region that WAF adds automatically.  
__Required__: No  
__Type__: String

#### SourceIPAddressSource  
How to determine the true source IP of requestors in logs.  SOURCE_IP (Default) is the TCP source IP seen by WAF.  Any other value will treat this value as a header name and use the value of this header as the source IP (e.g. X-FORWARDED-FOR)  
__Required__: No  
__Type__: String  
__Default__: `SOURCE_IP`  

_____

## Deployment scripts
### Create stack:
```
aws cloudformation create-stack --stack-name athena-workgroup-views \
--template-body file://code/athena/cfn/athena-workgroup-views.yaml \
--capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM CAPABILITY_IAM \
--parameters \
ParameterKey=WafLogsS3Bucket,ParameterValue=central-waf-logs-$PayerAccountId-$PrimaryRegion
```
