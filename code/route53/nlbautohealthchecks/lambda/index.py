import sys
sys.path.insert(0,'./route53/lambda/nlbHC')
import json, boto3, random, os, cfnresponse, time, logging, botocore
from create_health_check_nlb import create_health_check_nlb
from delete_health_checks import delete_health_checks

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

r53_client = boto3.client('route53')
sqs_client = boto3.client('sqs')
cw_client = boto3.client('cloudwatch')
elbv2_client = boto3.client('elbv2')
shield_client = boto3.client('shield')

queueUrl = os.environ['sqsQueueURL']
accountId = os.environ['AccountId']
def lambda_handler(event, context):
    logger.info (event)
    responseData = {}
    #If a call from a custom lambda backed resource
    if 'RequestType' in event:
        if (event['RequestType'] == 'Create' or event['RequestType'] == 'Update'):
            elbv2s = elbv2_client.describe_load_balancers()
            logger.debug(elbv2s)
            logger.info("Created synthetic create message so we try again later but CFN can finish")
            for elb in elbv2s['LoadBalancers']:
                try:
                    if elb['Type'] == 'network':
                        lbAddressList = []
                        for az in elb['AvailabilityZones']:
                            logger.debug(az)
                            if az['LoadBalancerAddresses'] != []:
                                lbAddressList.append({"ipAddress": az['LoadBalancerAddresses'][0]['IpAddress'],"allocationId": az['LoadBalancerAddresses'][0]['AllocationId']})
                            if lbAddressList != []:
                                message = {
                                        	"detail": {
                                        		"eventName": "CreateLoadBalancer",
                                        		"requestParameters": {
                                        			"type": "network"},
                                        		"responseElements": {
                                        			"loadBalancers": [{
                                        				"loadBalancerArn": elb['LoadBalancerArn'],
                                        				"availabilityZones": [{
                                        					"loadBalancerAddresses": lbAddressList
                                            				}]
                                            			}]
                                            		}
                                            	}
                                            }
                                response = sqs_client.send_message(
                                    QueueUrl=queueUrl,
                                    MessageBody=json.dumps(message),
                                    DelaySeconds=5
                                    )
                                logger.debug(response)
                    else:
                        logger.info("Skipping: " + elb['Type'])
                except botocore.exceptions.ClientError as error:
                    logger.error(error.response['Error']['Message'])
                    cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "CFNCall - " + event['RequestType'])
                    return()
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CFNCall - " + event['RequestType'])
        elif event['RequestType'] == 'Delete':
            elbv2s = elbv2_client.describe_load_balancers()
            for elb in elbv2s['LoadBalancers']:
                try:
                    if elb['Type'] == 'network':
                        delete_health_checks(elb['LoadBalancerArn'].split('/')[2])
                    else:
                        logger.info ("Skipping: " + elb['Type'])
                except botocore.exceptions.ClientError as error:
                    logger.error(error.response['Error']['Message'])
                    cfnresponse.send(event, context, cfnresponse.FAILED, responseData, "CFNCall - " + event['RequestType'])
                    return()
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CFNCall - " + event['RequestType'])
    elif 'Records' in event:
        for record in event['Records']:
            recordEvent = json.loads(record['body'])
            logger.debug("recordEvent")
            logger.debug(recordEvent)
            logger.debug(recordEvent['detail']['eventName'])
            #Creating a new nlb
            if recordEvent['detail']['eventName'] == "CreateLoadBalancer":
                if ('type' in recordEvent['detail']['requestParameters']):
                    if (recordEvent['detail']['requestParameters']['type'] == 'network'):
                        for lb in recordEvent['detail']['responseElements']['loadBalancers']:
                            allocationIds = []
                            for az in lb['availabilityZones']:
                                allocationIds.append(az['loadBalancerAddresses'][0]['allocationId'])
                            response = create_health_check_nlb(lb['loadBalancerArn'],allocationIds)
                            if response == "The referenced protection does not exist.":
                                raise Exception("Not Shield Protected, exiting ungracefully for SQS retry to check later")
            if recordEvent['detail']['eventName'] == "DeleteLoadBalancer":
                logger.debug("TriggeredDelete")
                if ('loadBalancerArn' in recordEvent['detail']['requestParameters']):
                    lbArn = recordEvent['detail']['requestParameters']['loadBalancerArn']
                    lbType = lbArn.split('/')[1]
                    logger.debug (lbArn)
                    logger.debug (lbType)
                    if lbType == 'net':
                        logger.debug("Call Delete Health Checks")
                        #delete_health_checks(nlbArn)
                        delete_health_checks(recordEvent['detail']['requestParameters']['loadBalancerArn'].split('/')[2])
                    else:
                        logger.info("Skipping: " + lbType)
            #Changing Tags for an nlb
            if recordEvent['detail']['eventName'] in ["AddTags","RemoveTags","CreateListener","ModifyListener","DeleteListener"]:
                if 'resourceArns' in recordEvent['detail']['requestParameters']:
                    for lbArn in recordEvent['detail']['requestParameters']['resourceArns']:
                        lbType = lbArn.split('/')[1]
                        if lbType == 'net':
                            response = create_health_check_nlb(recordEvent['detail']['requestParameters']['resourceArns'][0])
                            if response == "The referenced protection does not exist.":
                                raise Exception("Not Shield Protected, exiting ungracefully for SQS retry to check later")
                        else:
                            logger.info("Skipping: " + lbType)
