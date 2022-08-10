import os
import json
import boto3
import logging
import sys

sys.path.insert(0,'./route53/config-proactive-engagement/lambda/cfn-stack-manage')
from cfn_stack_manage import *
from botocore.exceptions import ClientError
from botocore.config import Config

config = Config(
   retries = {
      'max_attempts': 3,
      'mode': 'standard'
   }
)

sqs_client = boto3.client("sqs", region_name=os.getenv('AWS_REGION'), config=config)
config_client = boto3.client('config', region_name=os.getenv('AWS_REGION'), config=config)
stackSetNameKeyWord = "StackSet-proactive-engagement"

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

def delete_queue_item(msg):
    entries = [{'Id': msg['MessageId'], 'ReceiptHandle': msg['ReceiptHandle']}]
    resp = sqs_client.delete_message_batch(
        QueueUrl = os.getenv('SQS_QUEUE_URL'),
        Entries = entries
    )
    if (len(resp['Successful'])!=len(entries)):
        raise RuntimeError(f'Failed to delete message: entries={entries!r} resp={resp!r}')
    logger.info(f"SQS Message deleted: {msg['MessageId']}")
    
def get_number_of_messages_in_queue():
    response = sqs_client.get_queue_attributes(
        QueueUrl = os.getenv('SQS_QUEUE_URL'),
        AttributeNames = ['ApproximateNumberOfMessages',]
    )
    number_of_messages = int(response['Attributes']['ApproximateNumberOfMessages'])
    logger.info(f"Number of messages in the SQS queue: {number_of_messages}")
    return number_of_messages

def receive_messages_from_queue():
    try:
        number_of_messages = get_number_of_messages_in_queue()
        msg_count = int(os.getenv('MSGS_TO_BE_PROCESSED'))
        if msg_count>number_of_messages:
            msg_count = number_of_messages
        for i in range(msg_count):
            response = sqs_client.receive_message(
                QueueUrl = os.getenv('SQS_QUEUE_URL'),
                MaxNumberOfMessages = 1,
                AttributeNames = ["All"],
                WaitTimeSeconds = 10
            )
            yield from response['Messages']
    
    except (ClientError, TypeError, OSError) as exc:
        logger.exception("Unknown Exception: " + str(exc))

def process_messages(messages):
    response = {}
    try:
        for msg in messages:
            message_id = msg['MessageId']
            message_body = json.loads(msg["Body"])

            cfn_parameters = message_body["cfnParameters"]
            resoure_id = message_body["resoureId"]
            template_url = message_body["templateURL"]

            logger.info({"MessageID": message_id, "cfn_parameters": cfn_parameters, "resource_id": resoure_id, "template_url": template_url})

            stack_manage_response = cfn_stack_manage(cfn_parameters, resoure_id, template_url)

            delete_queue_item(msg)
            response.update({message_id: stack_manage_response})
            # response.update(stack_manage_response)
    except Exception as exc:
        logger.debug("I am in Except", exc)
        logger.error("Exception in process_messages(): ", exc)

def get_config_rule_status(rule):
    try:
        logger.debug("Inside config rule status check")
        response = config_client.describe_compliance_by_config_rule(
                    ConfigRuleNames=[
                        rule.get('ConfigRuleName'),
                    ],
                    ComplianceTypes=[
                        'NON_COMPLIANT'
                    ]
                )
        compliance_data = response.get('ComplianceByConfigRules')
        return compliance_data
    except AttributeError as ae:
        logger.error(f"No Config Rule found with Proactive Engagement. {ae}")

def invoke_config_rule_eval():
    config_response = config_client.describe_config_rules()
    rulesList = config_response['ConfigRules']
    rule = next((
        e for e in rulesList if stackSetNameKeyWord in e.get('ConfigRuleName')), None)
    print(rule)
    if rule is None:
        logger.error("No Config Rule found with Proactive Engagement")

    else:
        is_rule_non_compliant = get_config_rule_status(rule)
        if is_rule_non_compliant:
            logger.debug(f"config rule found and is non-compliant, invoking eval. config rule:: {rule.get('ConfigRuleName')}")
            config_client.start_config_rules_evaluation(
                ConfigRuleNames=[
                    rule.get('ConfigRuleName')
                ]
            )
        else:
            logger.info(f"The rule {rule.get('ConfigRuleName')} is compliant")
            
    logger.debug("invoke config rule eval complete")

def lambda_handler(event, context):
    try:
        # invoke_config_rule_eval()

        messages = receive_messages_from_queue()

        response = process_messages(messages)

        logger.info(response)

        return response

    except (ClientError, TypeError, OSError) as exc:
        logger.exception("Unknown Exception: " + str(exc))

