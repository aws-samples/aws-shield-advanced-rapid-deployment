import sys
sys.path.insert(0,'./route53/lambda/eipHC')
import json, boto3, random, os, cfnresponse, time, logging, botocore
from create_health_check_eip import create_health_check_eip
from delete_health_checks import delete_health_checks

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

ec2_client = boto3.client('ec2')
sqs_client = boto3.client('sqs')
cfn_client = boto3.client('cloudformation')
#Build a paginator, the number of stacks can easily be larger than a single list stack so we ensure we get all of them
cfn_paginator = cfn_client.get_paginator('list_stacks')
queueUrl = os.environ['sqsQueueURL']
accountId = os.environ['AccountId']

def lambda_handler(event, context):
    
    logger.debug(event)
    #If called by CloudFormation for create, update or delete actions
    responseData = {}
    #If called by CloudFormation for create, update or delete actions
    if 'RequestType' in event:
        logger.info("CFNRequestTriggered")
        try:
            addresses = ec2_client.describe_addresses(
                )['Addresses']
        except botocore.exceptions.ClientError as error:
            responseData['Error'] = error.response['Error']
            cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "FailedDescribingAddresses")
            logger.error(error.response['Error']['Message'])
            return ()
        if (event['RequestType'] == 'Create' or event['RequestType'] == 'Update'):
            for address in addresses:
                if 'InstanceId' in address:
                    try:
                        logger.info("Created synthetic create message so we try again later but CFN can finish")
                        message = {
                                    "account": accountId,
                                	"detail": {
                                		"eventName": "AssociateAddress",
                                		"requestParameters": {
                                			"instanceId": address['InstanceId'],
                                			"allocationId": address['AllocationId'],
                                			"domain": address['Domain']
                                		}
                                	}
                                }
                        logger.info(message)
                        response = sqs_client.send_message(
                            QueueUrl=queueUrl,
                            MessageBody=json.dumps(message),
                            DelaySeconds=5
                            )
                        logger.debug(response)
                    except botocore.exceptions.ClientError as error:
                        responseData['Error'] = error.response['Error']
                        logger.error(error.response['Error'])
                        cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "SQSSyntheticEventFailed")
                        return()
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CFNCreate")
        elif event['RequestType'] == 'Delete':
            logger.info("CFNDeleteCalled")
            cfnPaginate = cfn_paginator.paginate(
                                StackStatusFilter=[
                                    'CREATE_IN_PROGRESS',
                                    'CREATE_COMPLETE',
                                    'ROLLBACK_IN_PROGRESS',
                                    'ROLLBACK_COMPLETE',
                                    'UPDATE_IN_PROGRESS',
                                    'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
                                    'UPDATE_COMPLETE',
                                    'UPDATE_ROLLBACK_IN_PROGRESS',
                                    'UPDATE_ROLLBACK_FAILED',
                                    'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
                                    'UPDATE_ROLLBACK_COMPLETE'
                                    ]
                                )
            cfn_Response = (cfnPaginate.build_full_result())['StackSummaries']
            for c in cfn_Response:
                logger.debug("Checking: " + c['StackName'])
                if c['StackName'].startswith("eipalloc"):
                    n = c['StackName'].replace('-HealthChecks','')
                    logger.debug("Deleting Stack: " + n)
                    delete_health_checks(n)
            for address in addresses:
                logger.debug(address)
                try:
                    delete_health_checks(address['AllocationId'])
                except:
                    logger.debug("Failed To delete: " +address)
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CFNDeleteSuccessful")
    elif 'Records' in event:
        logger.debug("RecordFound")
        logger.info(event)
        for record in event['Records']:
            recordEvent = json.loads(record['body'])
            logger.info(recordEvent)
            logger.info(recordEvent['detail']['eventName'])
            if recordEvent['detail']['eventName'] == "AssociateAddress":
                if ('instanceId' in recordEvent['detail']['requestParameters']):
                    eipAlloc = recordEvent['detail']['requestParameters']['allocationId']
                    instanceId = recordEvent['detail']['requestParameters']['instanceId']
                    response = create_health_check_eip(eipAlloc, instanceId)
                    if response == "The referenced protection does not exist.":
                        raise Exception('Raise Exception for SQS to Retry')
            #Check when EC2 Instance tags are created/deleted to see if we need to create,update, or delete health checks
            if recordEvent['detail']['eventName'] in ["CreateTags","DeleteTags"]:
                instanceId = recordEvent['detail']['requestParameters']['resourcesSet']['items'][0]['resourceId']
                #We do this to get the allocation ID if this was to an instance.  If the resourceId is not an EC2 instance, the resposne will be empty and exit gracefully
                try:
                    ec2Response = ec2_client.describe_addresses(
                        Filters=[
                            {
                                'Name': 'instance-id',
                                'Values': [
                                    instanceId,
                                ]
                            }
                        ]
                    )['Addresses'][0]
                    logger.debug("ec2Response")
                    logger.debug(ec2Response)
                except botocore.exceptions.ClientError as error:
                    responseData['Error'] = error.response['Error']
                    logger.error(error.response['Error'])
                    cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "DescribeAddressesForTagChangeFailed")
                    return()                    
                if not ec2Response ==[]:
                    response = create_health_check_eip(ec2Response['AllocationId'], instanceId)
                    if response == "The referenced protection does not exist.":
                        raise Exception('Raise Exception for SQS to Retry')
            #There is not a way that I see to get the EC2 instance that was associated with an EIP after you disassociate it.
            #To ensure the right thing happens, we send synthetic associate events for EIP's associated instances
            elif recordEvent['detail']['eventName'] == "DisassociateAddress":
                logger.info("DisassociateAddress!")
                
                #Build list of existing addresses for VPC that have an Instance Id
                addresses = ec2_client.describe_addresses(
                    Filters=[
                        {
                            'Name': 'domain',
                            'Values': [
                                'vpc',
                            ]
                        }
                    ])['Addresses']
                logger.debug("addresses")
                logger.debug(addresses)
                stackPrefixList = []
                #Build list of eipAlloc where there is an active instance assocaited
                for address in addresses:
                    logger.debug(address)
                    if 'InstanceId' in address:
                        stackPrefixList.append("-".join([address['AllocationId'],address['NetworkInterfaceId'],address['PrivateIpAddress']]))
                logger.debug("stackPrefixList")
                logger.debug(stackPrefixList)
                #Get a list of all Stacks
                cfnPaginate = cfn_paginator.paginate(
                    StackStatusFilter=[
                        'CREATE_IN_PROGRESS',
                        'CREATE_COMPLETE',
                        'ROLLBACK_IN_PROGRESS',
                        'ROLLBACK_COMPLETE',
                        'UPDATE_IN_PROGRESS',
                        'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
                        'UPDATE_COMPLETE',
                        'UPDATE_ROLLBACK_IN_PROGRESS',
                        'UPDATE_ROLLBACK_FAILED',
                        'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
                        'UPDATE_ROLLBACK_COMPLETE'
                        ]
                    )
                cfn_Response = (cfnPaginate.build_full_result())['StackSummaries']
                existingStackList = []
                for c in cfn_Response:
                    if c['StackName'].startswith("eipalloc"):
                        existingStackList.append(c['StackName'].replace('-HealthChecks',''))
                    logger.debug(c['StackName'].replace('-HealthChecks',''))
                logger.debug(existingStackList)
                for stackPrefix in existingStackList:
                    logger.debug(stackPrefix)
                    if not stackPrefix in stackPrefixList:
                        logger.debug("Delete This Stack")
                        logger.debug(stackPrefix)
                        delete_health_checks(stackPrefix)
                    else:
                        logger.debug("Stack for alloc should continue to exist")

