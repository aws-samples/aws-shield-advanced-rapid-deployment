import boto3
import json
import os
import zipfile
import botocore
#Get AccountId
path = os.getcwd()
accountId = boto3.client('sts').get_caller_identity()['Account']
f = open(path + '/config.json')
config = json.load(f)
f.close()
#Create Zip of directory
if not os.path.isdir(path + '/artifacts'):
    os.mkdir(path + '/artifacts')
zipf = zipfile.ZipFile('artifacts/lambda.zip', 'w', zipfile.ZIP_DEFLATED)
for root, dirs, files in os.walk(path + "/code"):
    for file in files:
        if file.split('.')[-1] == 'py':
            zipf.write(os.path.join(root, file), 
                       os.path.relpath(os.path.join(root, file).replace(os.getcwd()+'/code','/'), 
                                       os.path.join(path, '..')))
zipf.close()
for region in config['Regions']:
    print (region)
    bucketName = "-".join([config['BucketPrefix'],accountId,region])
    client = boto3.client('s3',region_name=region)
    s3 = boto3.resource('s3',region_name=region)

    try:
        if region == 'us-east-1':
            client.create_bucket(
                Bucket=bucketName
            )
        else:
            client.create_bucket(
                Bucket=bucketName,
                CreateBucketConfiguration={
                    'LocationConstraint': region
                }
            )
    except botocore.exceptions.ClientError as error:
        if not error.response['Error']['Code'] == "BucketAlreadyOwnedByYou":
            print (error.response)
            break
    #If you include Org ID, add a bucket policy allowing accounts in Org to GetObject
    if "OrgId" in config:
        r =client.put_bucket_policy(
            Bucket=bucketName,
            ConfirmRemoveSelfBucketAccess=True,
            Policy=json.dumps({
                        "Version": "2012-10-17",
                        "Id": "OrgAccessToCodeInBucket",
                        "Statement": [
                    {
                                "Sid": "AllowGetFromOrg",
                                "Effect": "Allow",
                                "Principal": "*",
                                "Action": "s3:GetObject",
                                "Resource": "arn:aws:s3:::" + bucketName + "/*",
                                "Condition": {
                                    "StringEquals": {
                                        "aws:PrincipalOrgID": config['OrgId']
                                    }
                                }
                            }
                        ]
                    }),
            ExpectedBucketOwner=accountId
        )
    s3.meta.client.upload_file('artifacts/lambda.zip', bucketName, 'lambda.zip')
    for root, dirs, files in os.walk(path + "/code"):
        for file in files:
            s3key = (root.replace(path + "/",'') +  "/" + file)
            if file.endswith("yaml"):
                print ("https://" + bucketName + ".s3.amazonaws.com/" + s3key)
            s3.meta.client.upload_file(root + "/" + file, bucketName, s3key)
            


        

