import boto3
import json
import os
import zipfile
import botocore
#Get AccountId
path = os.getcwd()
accountId = boto3.client('sts').get_caller_identity()['Account']

#Retrieve relevant environment variables
config = {}
config['Regions'] = os.environ['Regions'].split(' ')
config['BucketPrefix'] = os.environ['BucketPrefix']
config['OrgId'] = os.environ['OrgId']
#Create Zip of directory
if not os.path.isdir(path + '/artifacts'):
    os.mkdir(path + '/artifacts')
    
def zip_directory(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, mode='w') as zipf:
        len_dir_path = len(folder_path)
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.split('.')[-1] == 'py':
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, file_path[len_dir_path:])
zip_directory('code/','artifacts/lambda.zip')
for region in config['Regions']:
    print (region)
    bucketName = "-".join([config['BucketPrefix'],accountId,region])
    client = boto3.client('s3',region_name=region)
    ssm_client = boto3.client('ssm',region_name=region)
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
    try:
        ssm_client.put_parameter(
            Name='shield-advanced-ddos-automation-bucket',
            Value=bucketName,
            Type='String',
            Overwrite=True
            )
    except botocore.exceptions.ClientError as error:
        #if not error.response['Error']['Code'] == "BucketAlreadyOwnedByYou":
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
            print (s3key)
            print (root)
            print (path + "/")
            if file.endswith("yaml"):
                print ("https://" + bucketName + ".s3.amazonaws.com/" + s3key)
            s3.meta.client.upload_file(root + "/" + file, bucketName, s3key)
            


        

