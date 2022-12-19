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
#enabledProactiveEngagement = os.environ['EnabledProactiveEngagement']
#enableSRTAccess = os.environ['EnableSRTAccess']
#emergencyContactCount = os.environ['EmergencyContactCount']
#srtAccessRoleName = os.environ['SrtAccessRoleName']
#Build Emergency Contact List

def lambda_handler(event, context):
    logger.debug(event)
    enabledProactiveEngagement = event['ResourceProperties']['EnabledProactiveEngagement']
    emergencyContactCount = int(event['ResourceProperties']['EmergencyContactCount'])
    enableSRTAccess = event['ResourceProperties']['EnableSRTAccess']
    srtAccessRoleName = event['ResourceProperties']['SRTAccessRoleName']    
    responseData = {}
    if "RequestType" in event:
        if event['RequestType'] in ['Create','Update']:
            try:
                logger.debug("Start Create Subscription")
                shield_client.create_subscription()
                logger.info ("Shield Enabled!")
            except botocore.exceptions.ClientError as error:
                if error.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                    logger.info ("Subscription already active")
                else:
                    logger.debug("Failed Create Subscription")
                    logger.error(error.response['Error'])
                    responseData['Error'] = error.response['Error']
                    cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SubscribeFailed")
                    return ()
        else:
            responseData = {}
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CFNDeleteGracefulContinue")
            return()
    #try:
    logger.debug("Start build Contacts")
    emergencyContactList = []
    emergencyContactList.append({
        "EmailAddress": event['ResourceProperties']['EmergencyContactEmail1'],
        "PhoneNumber": event['ResourceProperties']['EmergencyContactPhone1']
        })
    if emergencyContactCount == 2:
        emergencyContactList.append({
            "EmailAddress": event['ResourceProperties']['EmergencyContactEmail2'],
            "PhoneNumber": event['ResourceProperties']['EmergencyContactPhone2']
            })
    logger.debug("emergencyContactList")
    logger.debug(emergencyContactList)
    #except KeyError as error:
        #logger.debug("Error Setting Contacts")
        #logger.debug(error)
        #responseData = {}
        #cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "BuildContactListFailed")
        #return ()

    #Activate Shield Subscription
    #Create SRT Role if needed
    try:
        logger.debug("Start Get current SRT Role")
        iam_role_response = iam_client.get_role(
            RoleName=srtAccessRoleName
            )
        roleArn = iam_role_response['Role']['Arn']
        logger.debug ("AWS SRTAccess already exists")
    except botocore.exceptions.ClientError as error:
        logger.debug("Start Create SRT Role")
        if error.response['Error']['Code'] == 'NoSuchEntity':
            try:
                iam_role_response = iam_client.create_role(
                    RoleName=srtAccessRoleName,
                    AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[{"Sid":"","Effect":"Allow","Principal":{"Service":"drt.shield.amazonaws.com"},"Action":"sts:AssumeRole"}]}',
                    MaxSessionDuration=3600,
                )
                roleArn = iam_role_response['Role']['Arn']
            except botocore.exceptions.ClientError as error:
                logger.debug("Failed Create SRT Role")
                logger.error(error.response['Error'])
                responseData['Error'] = error.response['Error']
                cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "CreateSRTRoleFailed")
                return ()
        else:
            logger.error(error.response['Error'])
            responseData['Error'] = error.response['Error']
            cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SRTRolePolicyConfigFailed")
            return ()
    #Ensure SRT Policy Attached to Role
    try:
        logger.info("Listing attached role policies for AWSSRTAccess role.")
        iam_response = iam_client.list_attached_role_policies(
            RoleName=srtAccessRoleName
            )
        policyList = []
        for p in iam_response['AttachedPolicies']:
            policyList.append(p['PolicyName'])
        if 'AWSShieldSRTAccessPolicy' not in policyList:
            logger.info("Required Policy not attached to role, attaching")
            response = iam_client.attach_role_policy(
                RoleName=srtAccessRoleName,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSShieldDRTAccessPolicy'
                )
        else:
            logger.debug ("Required Policy Already attached")
    except botocore.exceptions.ClientError as error:
        logger.debug("Failed making SRT Role policies correct")
        logger.error(error)
        responseData['Error'] = error.response['Error']
        cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SRTRolePolicyConfigFailed")
        return ()

    if enableSRTAccess == 'true':
        logger.debug("Start Enable SRT Access")
        try:
            logger.info("Associating SRT role.")
            shield_response = shield_client.associate_drt_role(
                RoleArn=roleArn
                )
        except botocore.exceptions.ClientError as error:
            logger.debug("Failed Enable SRT Access")
            logger.error(error)
            responseData['Error'] = error.response['Error']
            cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SRTEnablementFailed")
            return ()
    else:
        try:
            logger.info("Describing SRT access.")
            shield_SRT_response = shield_client.describe_SRT_access()
            if 'RoleArn' in shield_SRT_response:
                logger.info("Disassociating SRT role.")
                shield_SRT_response = shield_client.disassociate_SRT_role()
        except botocore.exceptions.ClientError as error:
            logger.error(error)
            responseData['Error'] = error.response['Error']
            cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SRTDisableFailed")
            return ()
    try:
        logger.info("Start Updating emergency contact settings.")
        shield_response = shield_client.update_emergency_contact_settings(
            EmergencyContactList=emergencyContactList
            )
        logger.debug(shield_response)
    except botocore.exceptions.ClientError as error:
        logger.info("Failed Updating emergency contact settings.")
        logger.error(error)
        responseData['Error'] = error.response['Error']
        cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "EmergencyContactUpdateFailed")
        return ()
    if enabledProactiveEngagement == 'true':
        try:
            logger.info("Start Associating proactive engagement details.")
            shield_client.associate_proactive_engagement_details(
                EmergencyContactList=emergencyContactList)
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'InvalidOperationException':
                logger.debug("Proactive Engagement has been configured before, making update API call instead")
                try:
                    shield_response = shield_client.update_emergency_contact_settings(
                            EmergencyContactList=emergencyContactList
                        )
                except botocore.exceptions.ClientError as error:
                    logger.debug(error.response)
                    responseData['Error'] = error.response['Error']
                    cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "ProactiveEngagementEnableFailed")
                    return ()
            else:
                logger.debug(error.response)
                logger.error(error)
                responseData['Error'] = error.response['Error']
                cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "ProactiveEngagementEnableFailed")
                return ()

            logger.info("Enabling proactive engagement.")
            #shield_subscription = client.describe_subscription()
            #logger.debug ("shield_subscription")
            #logger.debug(json.dumps(shield_subscription))
            logger.debug("Start enable_proactive_engagement")
            shield_response = shield_client.enable_proactive_engagement()
        except botocore.exceptions.ClientError as error:
            logger.debug(error.response)
            if error.response['Error']['Code'] == 'InvalidOperationException':
                print ("InvalidOperationException")
            elif error.response['Error']['Code'] == 'InvalidParameterException':
                logger.info("Error Enabling Proactive Support, continue regardless")
            else:
                logger.info("Failed Other: Associating proactive engagement details.")
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
