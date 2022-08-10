## Overview
Creates a lambda function and export called by the config-proactive-engagement module to associate a calculated healthcheck with a shield protection ID.

_____

## CloudFormation Details
__Template__: route53/route53-associate-shield-protection/cfn/route53-associate-shield-protection.yaml  
__Mechanism__: CloudFormation StackSet  
__Location(s)__: All accounts  
__Region(s)__: All Regions

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


#### Remediation
S3 Key path to zip file.  By default, this should be the same for all parameters with this name

__Required__: No  
__Type__: String  
__Default__: True  
__AllowedValues__:  
  * True  
  * False  

#### ALBHealthCheckKey
Default CloudFormation template for auto-remediation of ALB resources.

__Required__: No  
__Type__: String  
__Default__: code/route53/healthChecks/alb-health-check.yaml

#### CloudfrontHealthCheckKey
Default CloudFormation template for auto-remediation of CloudFront resources

__Required__: No  
__Type__: String  
__Default__: code/route53/healthChecks/cf-health-check.yaml


#### EIPEC2HealthCheckKey
Default CloudFormation template for auto-remediation of EIPs associated with EC2 resources.

__Required__: No  
__Type__: String  
__Default__: code/route53/healthChecks/eip-health-check.yaml


#### NLBHealthCheckKey
Default CloudFormation template for auto-remediation of CloudFront resources.

__Required__: No  
__Type__: String  
__Default__: code/route53/healthChecks/nlb-health-check.yaml

#### CloudFrontForceEnableEnhancedMetrics
If CloudFront should have additional metrics enabled.  This must be in place for CloudFront distributions to use default (recommended metrics)

__Required__: No  
__Type__: String  
__Default__: Yes  
__AllowedValues__:
  * Yes
  * No

#### HealthCheckRegions
"Comma separated list of regions to complete Route 53 health checks from.  See [Route 53 supported regions](https://docs.aws.amazon.com/Route53/latest/APIReference/API_HealthCheckConfig.html#Route53-Type-HealthCheckConfig-Regions) for a list of valid options.  Note, this must include at least three regions

__Required__: No  
__Type__: String  
__Default__: us-east-1,us-west-2,eu-west-1

#### CheckTags
JSON list of tag and/or tag/values to scope resources.

__Required__: No  
__Type__: String  
__Default__: []
__AllowedValues__: See [CheckTags](/references/checktag.md)

#### snsTopicDetails
The accountID and SNS topic name in the format <AccountId>|<SnsTopicName>.  e.g. 111111111111|mySnsTopic.  This is used to calculate the regional ARN for SNS topics.

__Required__: Yes  
__Type__: String

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
ParameterKey=CodeS3BucketPrefix,ParameterValue=$BucketPrefix-$PayerAccountId \
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
