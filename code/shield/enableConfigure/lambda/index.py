import sys
sys.path.insert(0,'./shield/enableConfigure/lambda')
import json
import boto3
import os
import botocore
import urllib3
import cfnresponse
import logging

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

shield_client = boto3.client('shield')
iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
#Get Shield Config Values and Options
enabledProactiveEngagement = os.environ['EnabledProactiveEngagement']
enableDRTAccess = os.environ['EnableDRTAccess']
emergencyContactCount = os.environ['EmergencyContactCount']
accountId = os.environ['AccountId']
#Build Emergency Contact List

def lambda_handler(event, context):
    logger.debug(event)
    responseData = {}
    if "RequestType" in event:
        if event['RequestType'] in ['Create','Update']:
            try:
                shield_client.create_subscription()
                logger.info ("Shield Enabled!")
            except botocore.exceptions.ClientError as error:
                if error.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                    logger.info ("Subscription already active")
                else:
                    logger.error(error.response['Error'])
                    responseData['Error'] = error.response['Error']
                    cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SubscribeFailed")
                    return ()
        else:
            responseData = {}
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CFNDeleteGracefulContinue")
            return()
    try:
        emergencyContactList = []
        emergencyContactList.append({
            "EmailAddress": os.environ['EmergencyContactEmail1'],
            "PhoneNumber": os.environ['EmergencyContactPhone1']
            })
        if emergencyContactCount == 2:
            emergencyContactList.append({
                "EmailAddress": os.environ['EmergencyContactEmail2'],
                "PhoneNumber": os.environ['EmergencyContactPhone2']
                })
    except KeyError as error:
        responseData = {}
        responseData['Error'] = "KeyError for: " + error
        cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "BuildContactListFailed")
        return ()

    #Activate Shield Subscription
    #Create DRT Role if needed
    try:
        iam_role_response = iam_client.get_role(
            RoleName='AWSSRTAccess'
            )
        roleArn = iam_role_response['Role']['Arn']
        logger.debug ("AWS SRTAccess already exists")
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'NoSuchEntity':
            try:
                iam_role_response = iam_client.create_role(
                    RoleName='AWSSRTAccess',
                    AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[{"Sid":"","Effect":"Allow","Principal":{"Service":"drt.shield.amazonaws.com"},"Action":"sts:AssumeRole"}]}',
                    MaxSessionDuration=3600,
                )
                roleArn = iam_role_response['Role']['Arn']
            except:
                logger.error(error.response['Error'])
                responseData['Error'] = error.response['Error']
                cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "CreateDRTRoleFailed")
                return ()
        else:
            logger.error(error.response['Error'])
            responseData['Error'] = error.response['Error']
            cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SRTRolePolicyConfigFailed")
            return ()
    #Ensure DRT Policy Attached to Role
    try:
        logger.info("Listing attached role policies for AWSSRTAccess role.")
        iam_response = iam_client.list_attached_role_policies(
            RoleName='AWSSRTAccess'
            )
        policyList = []
        for p in iam_response['AttachedPolicies']:
            policyList.append(p['PolicyName'])
        if 'AWSShieldDRTAccessPolicy' not in policyList:
            logger.info("Required Policy not attached to role, attaching")
            response = iam_client.attach_role_policy(
                RoleName='AWSSRTAccess',
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSShieldDRTAccessPolicy'
                )
        else:
            logger.debug ("Required Policy Already attached")
    except botocore.exceptions.ClientError as error:
        logger.error(error)
        responseData['Error'] = error.response['Error']
        cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SRTRolePolicyConfigFailed")
        return ()

    if enableDRTAccess == 'true':
        try:
            logger.info("Associating DRT role.")
            shield_response = shield_client.associate_drt_role(
                RoleArn=roleArn
                )
        except botocore.exceptions.ClientError as error:
            logger.error(error)
            responseData['Error'] = error.response['Error']
            cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SRTEnablementFailed")
            return ()
    else:
        try:
            logger.info("Describing DRT access.")
            shield_drt_response = shield_client.describe_drt_access()
            if 'RoleArn' in shield_drt_response:
                logger.info("Disassociating DRT role.")
                shield_drt_response = shield_client.disassociate_drt_role()
        except botocore.exceptions.ClientError as error:
            logger.error(error)
            responseData['Error'] = error.response['Error']
            cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SRTDisableFailed")
            return ()

    try:
        logger.info("Updating emergency contact settings.")
        shield_response = shield_client.update_emergency_contact_settings(
            EmergencyContactList=emergencyContactList
            )
        logger.debug(shield_response)
    except botocore.exceptions.ClientError as error:
        logger.error(error)
        responseData['Error'] = error.response['Error']
        cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "EmergencyContactUpdateFailed")
        return ()

    if enabledProactiveEngagement == 'true':
        try:
            logger.info("Enabling proactive engagement.")
            shield_response = shield_client.enable_proactive_engagement()
            logger.info("Associating proactive engagement details.")
            shield_client.associate_proactive_engagement_details(
                EmergencyContactList=emergencyContactList)
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'InvalidOperationException':
                logger.info("ProactiveEngagementAlreadyEnabled")
            elif error.response['Error']['Code'] == 'InvalidParameterException':
                logger.info("Error Enabling Proactive Support, continue regardless")
            else:
                logger.error(error)
                responseData['Error'] = error.response['Error']
                cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "ProactiveEngagementEnableFailed")
                return ()
    else:
        try:
            logger.info("Disabling proactive engagement.")
            shield_response = shield_client.disable_proactive_engagement()
        except botocore.exceptions.ClientError as error:
            logger.error(error)
            responseData['Error'] = error.response['Error']
            cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "ProactiveEngagementEnableFailed")
            return ()

    responseData = {}
    cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "ConfigureShieldAdvancedSucceesful")
    return()
