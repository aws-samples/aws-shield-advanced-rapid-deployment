# AWS Shield Advanced Rapid Deployment
Practical and functional code to implement AWS services for DDoS Protection all through automation and with minimal coding required.
Code includes a series of CloudFormation templates with supporting lambda for custom lambda backed resources.  Each module can be deployed stand alone but
has been designed to be deployed as StackSets to protect multiple account(s), OU(s), or an entire AWS Organization and even in multiple regions.

## Building distributable for customization
* Update config.json as required
* Regions: list of AWS regions to create a S3 bucket and sync code and zip artifact
* BucketPrefix: used to construct s3 bucket names.  Buckets are named ${BucketPrefix}-${AWS::AccountId}-${AWS::Region}
* OrgId (Optional): If configured, a bucket policy is also added allowing accounts under the listed OrgId GetObject.  If you do not configure this, you will need to add your own bucket policy

* Now build and deploy the distributables to Amazon S3 buckets:
```
pip3 install -r requirements.txt
python3 setup.py
```
