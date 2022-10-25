import json
import sys
import logging
import botocore
sys.path.insert(0,'./route53/config-proactive-engagement/lambda/cfn-stack-manage')
from cfn_stack_manage import *

class CustomError(Exception):
    pass


logger = logging.getLogger('hc')

logger.setLevel('INFO')
logger.setLevel('DEBUG')


def lambda_handler(event, context):
    print (json.dumps(event))
    for record in event['Records']:
        body = json.loads(record['body'])
        readyToAct = current_cfn_in_progress()
        logger.debug ("Ready To Act: " + str (readyToAct))
        if readyToAct:
            response = process_message(body)
            delete_queue_item(record, response)
        else:
            raise CustomError("Current max number of stacks being processed, raising to check again later")