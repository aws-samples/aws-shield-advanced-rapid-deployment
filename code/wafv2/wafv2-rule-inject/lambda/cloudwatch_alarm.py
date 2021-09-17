import boto3, copy, logging, botocore, os

cw_client = boto3.client('cloudwatch')
aws_region = os.environ['AWS_REGION']
snsTopicDetails = os.environ['snsTopicDetails']
snsaccountID = snsTopicDetails.split("|")[0]
snsTopicName = snsTopicDetails.split("|")[1]
#Construct regional ARN from SNSDetails
snsTopicArn = ":".join(["arn:aws:sns",aws_region,snsaccountID, snsTopicName])

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

def create_alarm(wACLName):
    cw_data = {
        "AlarmName": "AlarmForRBRule_"+ wACLName + "_RateBasedLimit_BLOCK",
        "ActionsEnabled": True,
        "MetricName": "BlockedRequests",
        "Namespace": "AWS/WAFV2",
        "Dimensions": [
          {
            "Name": "WebACL",
            "Value": wACLName
          },
          {
            "Name": "Rule",
            "Value": "RateBasedLimit"
          },
          {
            "Name": "Region",
            "Value": aws_region
          }          
        ],
        "Period": 60,
        "Statistic": "Sum",
        "ComparisonOperator": "GreaterThanThreshold",
        "Threshold": 0,
        "EvaluationPeriods": 1,
        "TreatMissingData": "notBreaching"
    }
    if snsTopicArn != "":
        cw_data["AlarmActions"] = [snsTopicArn]
    try:
        response = cw_client.put_metric_alarm(
                **cw_data
                )
    except botocore.exceptions.ClientError as error:
        logging.error(error.response['Error']['Message'])
        return (error)
    else:
        return (response)

def delete_alarm(wACLName):
    try:
        response = cw_client.delete_alarms(
            AlarmNames=[
                "AlarmForRBRule_"+ wACLName + "_RateBasedLimit_BLOCK"
            ]
        )
    except botocore.exceptions.ClientError as error:
        logging.error(error.response['Error']['Message'])
        return (error)
    else:
        return (response)
