import sys
sys.path.insert(0,'./waf/lambda/wafRateRuleInject/')
import json, os, boto3, cfnresponse, botocore, logging
from update_waf_rule import update_waf_rule as update_waf_rule
from cloudwatch_alarm import create_alarm, delete_alarm

ec2_client = boto3.client('ec2')
waf_client = boto3.client('wafv2')

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

def lambda_handler(event, context):
    print (event)
    if 'detail' in event:
        if "errorCode" in event['detail']:
            return()
    #Cloudwatch Event trigger detected
    if 'detail-type' in event:
        logger.info("CloudWatch Event Call")
        logger.info (event['detail']['eventName'])
        if event['detail']['eventName'] == 'CreateWebACL':
            aclName = event['detail']['responseElements']['summary']['name']
            aclId = event['detail']['responseElements']['summary']['id']
        elif event['detail']['eventName'] == 'UpdateWebACL':
            aclName = event['detail']['requestParameters']['name']
            aclId = event['detail']['requestParameters']['id']
        elif event['detail']['eventName'] == 'DeleteWebACL':
            logger.info("No action on Delete WebACL")
            return()
        aclScope = event['detail']['requestParameters']['scope']
        update_waf_rule(aclName, aclId,aclScope)
    #CloudFormation call detected
    elif 'RequestType' in event:
        if event['RequestType'] == "Create" or event['RequestType'] == "Update":
            logger.info("CFN Call detected")
            #Get List of regional webACLs
            try:
                acls = waf_client.list_web_acls(
                    Scope='REGIONAL')
            except botocore.exceptions.ClientError as error:
                logger.error(error.response['Error']['Message'])
                cfnresponse.send(event, context, cfnresponse.FAILED, {})
                return ()
            for acl in acls['WebACLs']:
                logger.info(acl['Name'])
                update_waf_rule(acl['Name'], acl['Id'],'REGIONAL')
                response = create_alarm(acl['Name'])
                logger.info(response)
            #If in us-east-1, also get global WebACLs
            if (os.environ['AWS_REGION'] == 'us-east-1'):
                try:
                    acls = waf_client.list_web_acls(
                        Scope='CLOUDFRONT')
                except botocore.exceptions.ClientError as error:
                    logger.error(error.response['Error']['Message'])
                    cfnresponse.send(event, context, cfnresponse.FAILED, {})
                    return ()
                for acl in acls['WebACLs']:
                    logger.info(acl['Name'])
                    response = update_waf_rule(acl['Name'], acl['Id'], 'CLOUDFRONT')
                    logger.info(response)
                    response = create_alarm(acl['Name'])
                    logger.info(response)
        if event['RequestType'] == "Delete":
            logger.info("CFN Delete Call detected")
            try:
                acls = waf_client.list_web_acls(
                    Scope='REGIONAL')
            except botocore.exceptions.ClientError as error:
                logger.error(error.response['Error']['Message'])
                cfnresponse.send(event, context, cfnresponse.FAILED, {})
                return ()
            for acl in acls['WebACLs']:
                logger.info(acl['Name'])
                delete_alarm(acl['Name'])
            if (os.environ['AWS_REGION'] == 'us-east-1'):
                try:
                    acls = waf_client.list_web_acls(
                        Scope='CLOUDFRONT')
                except botocore.exceptions.ClientError as error:
                    logger.error(error.response['Error']['Message'])
                    cfnresponse.send(event, context, cfnresponse.FAILED, {})
                    return ()
                for acl in acls['WebACLs']:
                    logger.info(acl['Name'])
                    response = delete_alarm(acl['Name'])
                    logger.info(response)
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
