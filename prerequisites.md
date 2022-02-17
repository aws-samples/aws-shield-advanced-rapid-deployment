# Prerequisites

# Environment Variables

Automatic provisioning of perquisites and deployment scripts depend on a number of environment variable for copy/paste execution.  If you intend to use any of these, update each section and run them in your terminal to be referenced.


The below parameters must be updated based on your accounts/organization
```
export OrgId="o-########"
export PayerAccountId="111111111111"
export ParentRoot="r-1234"
export FMSAccountId="222222222222"
```


The below parameters can be optionally updated however defaults are acceptable for lab or non-lab usage

```
export Regions="us-east-1 us-east-2 us-west-2"
export BucketPrefix="shield-advanced-rapid-deployment"
export PrimaryRegion="us-east-1"
export memberAccountExecutionRole="arn:aws:iam::$MemberAccountId:role/AWSCloudFormationStackSetExecutionRole"
export fmsAccountExecutionRole="arn:aws:iam::$FMSAccountId:role/AWSCloudFormationStackSetExecutionRole"
```


# S3 Bucket and Code uploaded
Create an S3 bucket per region operating in, create access policies, and sync code to S3 buckets

Recommended accounts to implement include but are not limited to: Firewall Manager Delegated Administrator Account, Service Managed Stack Set Delegated Administrator account, security/shared services accounts.

##Automatic Provisioning of prerequisites


### Building distributable for customization


#### Local requirements
Have credentials configured via [environment variables](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) or [credentials file](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)




#### Build and deploy
setup.py will build s3 buckets and access policies based on the configured credentials and values of the above environment variables.  setup.py and also refresh if you make any changes, e.g. updates to code, additional regions, etc.

```
pip3 install -r requirements.txt
python3 setup.py
```


#### Outputs
Several modules have a parameter input of CodeS3BucketPrefix. Provide the following value when needed: ${BucketPrefix}-${AWS::AccountId} where AWS::AccountId is the account the buckets are created, e.g. shield-advanced-rapid-deployment-111111111111

## Manual Steps for prerequisites
Determine which region(s) you need to deploy into and retrieve the AWS Organization ID (e.g. o-1234abcd) for your organization.

For each region, create an s3 bucket with a common prefix and end with -${AWS::Region} representing the local region. The default value for automatic deployment is shield-advanced-rapid-deployment-${AWS::AccountId}-${AWS::Region}, e.g. shield-advanced-rapid-deployment-111111111111-us-east-1.  Note, it is critical that the prefix be the same for all regions to allow stack sets that deploy to multiple regions to calculate bucket names automatically.

Implement a bucket policy allowing all required accounts permission to GetObject to the entire bucket.  The automatic mechanism is a bucket policy based on PrincipalOrgId and is recommended as it will automatically cover new accounts as they are created.


#### Outputs
Several modules have a parameter input of CodeS3BucketPrefix.  This  will be the common suffix used for all buckets (without any region name)



---
# AWS Firewall Manager
Ensure [AWS Firewall Manager](https://docs.aws.amazon.com/waf/latest/developerguide/fms-prereq.html) has been enabled and if desired (recommended) a delegated administrator account specified.

___

#  Stack Sets

## Service Managed Stack Sets

Ensure [Service Managed stack sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-enable-trusted-access.html) are enabled. If needed, the central account you will deploy from is a delegated administrator for Service Managed Stack sets.

## Self Managed Stack Sets

Ensure [Self-Managed stack sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-prereqs-self-managed.html) are configured with the central deployment account having the administrator stack set role
