## Overview
Create a Firewall Manager Security Policy generate/transform mechanism for Security Policies for WAF

_____

## CloudFormation Details
__Template__: `code/fms/fms-policy-waf-generator/cfn/fms-policy-generator.yaml`  
__Mechanism__: `CloudFormation StackSet`  
__Location(s)__: `Firewall Manager delegated administrator`  
__Region(s)__: `All Regions`

_____
## How it works

#### Native CloudFormation
AWS Lambda function

#### Custom Lambda backed
Other CloudFormation stacks call this function as a custom lambda backed resource.  Lambda accepts an S3Key and retrieves a JSON object from the code S3 bucket.  Lambda transforms this JSON, implementing the appropriate logging confirmation, and placeholder values for rule groups with the matching name rule group ID.  See [Easy WAF Security Policy](../../easy_waf_security_policy.md)

_____

## Dependencies
[Service Managed Stack Sets](../../prerequisites.md)  
_____

## Parameter details:

#### CodeS3BucketPrefix
Modules use this consistent value to calculate the S3 bucket where relevant code is in place.  This includes lambda zip objects and other cfn templates for reference.  When consumed, the local region will be added as a suffix to this value.  
__Required:__: Yes  
__Type__: String  
__AllowedPattern__: See [Bucket naming rules](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html).  Note, the full bucket name will include the local region, ensure this value plus the longest region you intent to use is less than the maximum length for a bucket name allowed.

&nbsp;  
#### CodeS3Key
S3 Key path to zip file.  By default, this should be the same for all parameters with this name  
__Required__: Yes  
__Type__: String  
__Default__: `lambda.zip`    

_____

## Deployment scripts
### Create stack set
```
aws cloudformation create-stack-set \
--stack-set-name fms-policy-generato\
--template-body file://code/fms/fms-policy-waf-generator/cfn/fms-policy-generator.yaml \
--capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM CAPABILITY_IAM \
--permission-model SELF_MANAGED \
--execution-role-name AWSCloudFormationStackSetExecutionRole \
--administration-role-arn arn:aws:iam::$PayerAccountId:role/AWSCloudFormationStackSetAdministrationRole \
--parameters \
ParameterKey=CodeS3BucketPrefix,ParameterValue=$BucketPrefix-$PayerAccountId
```

### Add stacks to stack set
```
aws cloudformation create-stack-instances \
--stack-set-name fms-policy-generator \
--regions $Regions \
--deployment-targets Accounts=$FMSAccountId
```
