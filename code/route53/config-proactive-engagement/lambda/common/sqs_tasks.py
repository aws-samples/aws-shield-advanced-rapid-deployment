import boto3
import json
import os
import logging

from botocore.exceptions import ClientError

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

sqs_client = boto3.client('sqs')

def send_cfn_sqs_message(msg_body):
    try:
        response = sqs_client.send_message(QueueUrl=os.environ['SQS_QUEUE_URL'],
                                        MessageBody=json.dumps(msg_body))
        logger.debug("message_sent")
        logger.debug("msg_body")
        logger.debug(json.dumps(msg_body))
        logger.debug("response")
        logger.info(response)
    except ClientError:
        logger.exception(f'Could not send meessage')
        raise
    else:
        return response
