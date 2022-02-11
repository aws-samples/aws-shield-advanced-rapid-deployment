## Overview
Deploy a service managed stack set to all member accounts which subscribes and configures Shield Advanced.

_____

## CloudFormation Details
__Template__: shield/enableConfigure/cfn/shield-enable-configure.yaml  
__Mechanism__: CloudFormation StackSet  
__Location(s)__: All accounts  
__Region(s)__: Primary Region (us-east-1)

## How it works

#### Native CloudFormation
Lambda Function

#### Custom Lambda backed

A custom lambda backed resource is created and called to configure Shield Advanced.  Each configured component is enabled/configured/reconfigured based on the inputted parameter values.  Note, un-subscribing does not stop charges however disabled automatic renewal.  See [DeleteSubscription](https://docs.aws.amazon.com/waf/latest/DDOSAPIReference/API_DeleteSubscription.html)

_____

## Dependencies

* [Service Managed Stack Sets](../../prerequisites.md)  

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
__Minimum__: 1  
__Maximum__: 1024

#### EmergencyContactCount
Number of emergency contacts to configure

__Required__: Yes  
__Type__: Number  
__Default__: 1  
__Minimum__: 1  
__Maximum__: 2


#### EmergencyContactEmail1
E-mail address for Shield Advanced contact

__Required__: Yes  
__Type__: String  
__Minimum__: 1  
__Maximum__: 1024

#### EmergencyContactEmail2
E-mail address for Shield Advanced contact.

__Required__: Yes  
__Type__: String  
__Minimum__: 1  
__Maximum__: 1024

#### EmergencyContactPhone1
E-mail address for Shield Advanced contact

__Required__: Yes  
__Type__: String  
__Minimum__: 1  
__Maximum__: 1024

#### EmergencyContactPhone2
E-mail address for Shield Advanced contact

__Required__: Yes  
__Type__: String  
__Minimum__: 1  
__Maximum__: 1024

#### EnableProactiveEngagement
If Proactive Engagement feature should be enabled.  If yes, emergency contacts are also added to this feature

__Required__: Yes  
__Type__: Boolean  
__Default__: True


#### EnableDRTAccess
If SRT IAM role and permissions should be created and configured.

__Required__: Yes  
__Type__: Boolean  
__Default__: True

_____

## Deployment scripts
### Create stack Set

```
aws cloudformation create-stack-set \
--stack-set-name Enable-Shield-Advanced \
--template-body file://code/shield/enableConfigure/cfn/shield-enable-configure.yaml \
--capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM CAPABILITY_IAM \
--permission-model SERVICE_MANAGED \
--auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
--parameters \
ParameterKey=CodeS3BucketPrefix,ParameterValue=$BucketPrefix-$PayerAccountId \
ParameterKey=CodeS3Key,ParameterValue=lambda.zip \
ParameterKey=EmergencyContactCount,ParameterValue=2 \
ParameterKey=EmergencyContactEmail1,ParameterValue=someone@example.com \
ParameterKey=EmergencyContactEmail2,ParameterValue=someone@example.com \
ParameterKey=EmergencyContactPhone1,ParameterValue=+15555555555 \
ParameterKey=EmergencyContactPhone2,ParameterValue=+15555555555 \
ParameterKey=EnabledProactiveEngagement,ParameterValue=true \
ParameterKey=EnableDRTAccess,ParameterValue=false
```

### Add stacks to stack set
```
aws cloudformation create-stack-instances \
--stack-set-name Enable-Shield-Advanced \
--regions us-east-1 \
--deployment-targets OrganizationalUnitIds=$ParentRoot \
--operation-preferences RegionConcurrencyType=PARALLEL,MaxConcurrentPercentage=100
```
