## Overview
Deploy cloudwatch event to on a cron rate Shield Advanced protect Global Accelerators

_____


## CloudFormation details
__Template__: `fms/fms-mimic-shield-protect-global-accelerator/cfn/fms-mimic-shield-protect-global-accelerators.yaml`  
__Mechanism__: `CloudFormation StackSet`  
__Location(s)__: `All accounts`  
__Region(s)__: `us-west-2`  

_____

## How it works
#### Native CloudFormation
CloudWatch event, Lambda function

#### CloudWatch event (Cron) Driven
The created CloudWatch event invokes lambda every cron rate (default 1 hour).  Lambda lists all global accelerators, evaluates tags of resource to scope and ensure Shield Advanced protection is established when in scope.  AGA does not emit create/update events hence a cron rate.

### Custom Lambda Backed
On stack deployment, a custom lambda backed call is also made to Lambda.  This ensures protection is determined and implemented at deployment instead of potentially the next cron scheduled rate.

## Dependencies
* [Service Managed Stack Sets](../../prerequisites.md)  

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
__Required__: No  
__Type__: String  
__Default__: `lambda.zip`  

&nbsp;  
#### ScheduleExpression
CloudWatch event rate or cron to check for new Global accelerators  
__Required__: No  
__Type__: String  
__Default__: `rate(1 hour)`    
__AllowedPattern__: [CloudWatch Rate pattern](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions)

&nbsp;  
#### TagUsage
If value of CheckTags is for resources in scope or resources not in scope  
__Required__: No  
__Type__: String  
__Default__: `Include`  
__AllowedValues__: Include, Exclude  

#### CheckTags
JSON list of tag and/or tag/values to scope resources.  
__Required__: No  
__Type__: String  
__Default__: `[]`  
__AllowedValues__: See [CheckTags](../../references/checktags.md)  

_____

## Deployment scripts
### Create stack Set

```
aws cloudformation create-stack-set  
--stack-set-name fms-mimic-shield-protect-global-accelerators \
--template-body file://code/fms/fms-mimic-shield-protect-global-accelerator/cfn/fms-mimic-shield-protect-global-accelerators.yaml \
--capabilities CAPABILITY__AUTO__EXPAND CAPABILITY__NAMED__IAM CAPABILITY__IAM \
--permission-model SERVICE__MANAGED \
--auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
--parameters \
ParameterKey=CodeS3BucketPrefix,ParameterValue=$BucketPrefix-$PayerAccountId
```

### Add stacks to stack set
```
aws cloudformation create-stack-instances \
--stack-set-name fms-mimic-shield-protect-global-accelerators \
--regions us-west-2 \
--deployment-targets OrganizationalUnitIds=$ParentRoot \
--operation-preferences RegionConcurrencyType=PARALLEL,MaxConcurrentPercentage=100
```
