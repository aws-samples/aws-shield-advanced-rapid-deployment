import uuid
import time
import os
import json
import boto3
import logging
import sys
from datetime import datetime
import botocore
from botocore.config import Config


sqsQueueUrl = os.environ['SQS_QUEUE_URL']
CodeS3Bucket = os.environ['CodeS3Bucket']
maxConcurrent = 8

class CustomError(Exception):
    pass

sqs_client = boto3.client("sqs")
shield_client = boto3.client("shield")
config_client = boto3.client('config')
cfn_client = boto3.client('cloudformation')

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

def cfn_delete_stack(cfnStackName):
    #cfnStackName = ("HealthChecks-" + stackSuffix).replace("/","-")
    try:
        response = cfn_client.delete_stack(
            StackName=cfnStackName)
        return (response)
    except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error'])
        return (error.response['Error'])

def get_stack_current_state(cfnStackName):
    try:
      cfn_response = cfn_client.describe_stacks(
        StackName=cfnStackName)['Stacks'][0]
      logger.debug("cfn_response")
      logger.debug(cfn_response)
      cfnAction = cfn_response['StackStatus']
      logger.debug ("CFNAction: " + cfnAction)
    except botocore.exceptions.ClientError as error:
      if error.response['Error']['Message'] == "Stack with id " + cfnStackName + " does not exist":
        cfnAction = "DOESNOTEXIST"
      else:
        logger.error(error.response['Error'])
        return (error.response['Error']['Code'])
    print ("cfnAction:" + cfnAction)
    return (cfnAction)  
def clean_failed_stack(cfnStackName):
    logger.debug ("Start Failed Stack Cleanup")
    try:
      stackResources = cfn_client.describe_stack_resources(
        StackName=cfnStackName)['StackResources']
    except botocore.exceptions.ClientError as error:
      logger.error(error.response['Error'])
      return (error.response['Error']['Code'])
    #If any/all resources are any failed state, we need to ignore them to successfully delete the stack.  We need to send this out too for manual consumption.
    failedLogicalResources = []
    for resource in stackResources:
      if 'FAILED' in resource['ResourceStatus']:
        failedLogicalResources.append(resource['LogicalResourceId'])
    #Delete the stack
    try:
      cfn_client.delete_stack(
        StackName=cfnStackName,
        RetainResources=failedLogicalResources
      )
    except botocore.exceptions.ClientError as error:
      logger.error(error.response['Error'])
      return (error.response['Error']['Code'])
    logger.debug ("End Failed Action")
    return("KeepTrying")  
def cfn_stack_manage(cfnParameters, stackSuffix, templateURL):
    cfnStackName = ("HealthChecks-" + stackSuffix).replace("/","-")
    logger.info ("Stack Name: " + cfnStackName)
    clientRequestToken = str(uuid.uuid1())
    cfnAction = get_stack_current_state(cfnStackName)
    #For any type of failed state, delete with skip resources
    if 'FAILED' in cfnAction:
      response = clean_failed_stack(cfnStackName)
    elif cfnAction == "DOESNOTEXIST":
      logger.debug ("Start Need To Create")
      try:
        stackStatus = cfn_client.create_stack(
            StackName=cfnStackName,
            TemplateURL=templateURL,
            Parameters=cfnParameters,
            TimeoutInMinutes=2,
            OnFailure='DELETE',
            ClientRequestToken=clientRequestToken
        )
      except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ValidationError':
          logger.debug(error.response['Error'])
          return ("InvalidMessage")
        else:
          logger.error(error.response['Error'])
          return (error.response['Error']['Code'])
      logger.debug ("End Need To Create")
      return("KeepTrying")

    #Stack is steady.  Either start updating or confirm no updates needed
    elif 'COMPLETE' in cfnAction:
      logger.debug ("Stack exists in steady state, checking if updates are needed")
      try:
        cfn_client.update_stack(
          StackName=cfnStackName,
          TemplateURL=templateURL,
          Parameters=cfnParameters,
          ClientRequestToken=clientRequestToken
          )
          
      except botocore.exceptions.ClientError as error:
        if error.response['Error']['Message'] == 'No updates are to be performed.':
          logger.info("No CFN Update needed")
          return ("DeleteMessageOK")
        elif error.response['Error']['Code'] == 'ValidationError':
          logger.debug(error.response['Error'])
          return ("InvalidMessage")
        else:
          logger.error(error.response['Error'])
          return(error.response['Error'])
       #Stack is still creating or updating, wait
      logger.debug ("End Update Stack")
      return("KeepTrying")
    elif 'IN_PROGRESS' in cfnAction:
      return("KeepTrying")
    else:
      logger.debug ( "Something unexpected happened")
      return ("Error")

def delete_queue_item(record, response):
    if response == "DeleteMessageOK":
        entries = [{'Id': record['messageId'], 'ReceiptHandle': record['receiptHandle']}]
        resp = sqs_client.delete_message_batch(
            QueueUrl = sqsQueueUrl,
            Entries = entries
        )
        if (len(resp['Successful'])!=len(entries)):
            raise RuntimeError(f'Failed to delete message: entries={entries!r} resp={resp!r}')
        logger.info(f"Deleting SQS Message: {record['messageId']}")
        return ()
    elif response == "KeepTrying":
        logger.info(f"Keeping SQS Message: {record['messageId']}")
        #We need to raise so Lambda does not automatically delete the message    
        raise CustomError("Raise to prevent deleting message")
    elif response == 'InvalidMessage':
        logger.info("Invalid SQS Message, we can't process it")
        return()
def process_message(body):
    logger.debug ("Body")
    logger.debug (body)
    cfnAction = body['action']
    stackSuffix = body['stackSuffix']
    if cfnAction == 'Create':
        logger.debug("CFN Create detected")
        stack_managed_response = cfn_stack_manage(
          body["cfnParameters"],
          stackSuffix,
          body['templateURL']
          )
        logger.debug ('Process Message Response: ')
        logger.debug (stack_managed_response)
        return (stack_managed_response)
    elif cfnAction == 'Delete':
        logger.debug("CFN Delete detected")
        cfnStackName = ("HealthChecks-" + stackSuffix).replace("/","-")
        currentState = get_stack_current_state(cfnStackName)
        logger.debug("CurrentState: " + currentState)
        #If Steady, start delete
        if "COMPLETE" in currentState:
            stack_managed_response = cfn_delete_stack(cfnStackName)
            logger.debug('stack_managed_response')
            logger.debug(stack_managed_response)
            return ("KeepTrying")
        #In case the stack fails, force delete stack
        elif "FAILED" in currentState:
            response = clean_failed_stack(cfnStackName)
            return ("KeepTrying")
        #Stack deletes successfully, clear SQS message
        elif currentState == "DOESNOTEXIST":
            return("DeleteMessageOK")
        #Still active, need to wait for failed, completed, or doesn't exist state
        elif "IN_PROGRESS" in currentState:
          return ("KeepTrying")
        else:
          logger.debug("Currernt State didn't match any expected values")
          return ("InvalidMessage")
    else:
        logger.debug ("Unexpected CFN Action" + cfnAction)
        return ("Unexpected CFN Action" + cfnAction)

#Check how many current stacks are active.  We only want to allow so many at a given time
def current_cfn_in_progress():
    inProgressStacks = cfn_client.list_stacks(
        StackStatusFilter=[
            'CREATE_IN_PROGRESS',
            'ROLLBACK_IN_PROGRESS',
            'DELETE_IN_PROGRESS',
            'UPDATE_IN_PROGRESS',
            'UPDATE_ROLLBACK_IN_PROGRESS'
            ]
        )['StackSummaries']
    stackNameList = []
    for i in inProgressStacks:
      if i['StackName'].startswith("HealthChecks-"):
        stackNameList.append(i['StackName'])
    logger.debug(stackNameList)
    logger.debug("Current Number of In Progress Stacks: " + str(len(stackNameList)))
    if len (inProgressStacks) < maxConcurrent:
      return (True)
    else:
      return (False)