## Overview
Creates a lambda function and export called by the config-proactive-engagement module to associate a calculated healthcheck with a shield protection ID.

_____

## CloudFormation Details
__Run in__: `AWS Organizational MGMT/Administrator Account`
__Mechanism__: `CloudFormation StackSet`  
__Template__: `route53/route53-associate-shield-protection/cfn/route53-associate-shield-protection.yaml`  
__Deploy to__: `All accounts ` 
__Region(s)__: `regions specified within the “environment_variables.sh” file`

____
## How it works

#### Native CloudFormation
IAM Roles, Lambda function, CFN Export

#### Custom Lambda backed
Other CloudFormation stacks call this function as a custom lambda backed resource.  Lambda accepts a Shield Protection Id and route 53 health check Id.  Lambda then associates the inputted health check with the Shield Protection Id.

## Dependencies
[Service Managed Stack Sets](../../../prerequisites.md)  

_____

## Parameter details:

#### CodeS3BucketPrefix
Modules use this consistent value to calculate the S3 bucket where relevant code is in place.  This includes lambda zip objects and other cfn templates for reference.  When consumed, the local region will be added as a suffix to this value.

__Required:__: Yes  
__Type__: String  
__AllowedPattern__: See [Bucket naming rules](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html).  Note, the full bucket name will include the local region, ensure this value plus the longest region you intent to use is less than the maximum length for a bucket name allowed.


#### CodeS3Key
S3 Key path to zip file.  By default, this should be the same for all parameters with this name

__Required__: Yes  
__Type__: String  
__Default__: lambda.zip  

_____

## Deployment scripts
### Create stack Set

```
aws cloudformation create-stack-set \
--stack-set-name route53-associate-shield-protection \
--template-body file://code/route53/route53-associate-shield-protection/cfn/route53-associate-shield-protection.yaml \
--capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM CAPABILITY_IAM \
--permission-model SERVICE_MANAGED \
--auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
--parameters \
ParameterKey=CodeS3BucketPrefix,ParameterValue=$BucketPrefix-$FMSAccountId \
ParameterKey=CodeS3Key,ParameterValue=lambda.zip
```

### Add stacks to stack set
```
aws cloudformation create-stack-instances \
--stack-set-name route53-associate-shield-protection \
--regions $Regions \
--deployment-targets OrganizationalUnitIds=$ParentRoot \
--operation-preferences RegionConcurrencyType=PARALLEL,MaxConcurrentPercentage=100
```
