import json, boto3, random, os, cfnresponse, botocore, logging, time

r53_client = boto3.client('route53')
cw_client = boto3.client('cloudwatch')
cfn_client = boto3.client('cloudformation')
hc_regions = os.environ['HC_Regions'].split(',')

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

def delete_health_checks(cfnStackPrefix):
    cfnStackName = cfnStackPrefix + "-HealthChecks"
    waitForCFN = True
    timeKeeper = 0
    cfnAction = "evaluate"
    while waitForCFN:
         #This returns an error if the stack with the asked name does not exist.  If this is the case, we are updating
        try:
            cfn_response = cfn_client.describe_stacks(
                StackName=cfnStackName
                )['Stacks'][0]
            cfnAction = cfn_response['StackStatus']
            logger.debug ("cfn_response")
            logger.debug (cfn_response)
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Message'] == "Stack with id " + cfnStackName + " does not exist":
                return ()
        #Stack is steady and ready deleted
        if cfnAction in ['UPDATE_COMPLETE','CREATE_COMPLETE']:
            try:
                cfn_delete_response = cfn_client.delete_stack(
                    StackName=cfnStackName
                )
                logger.info("Deleting Stack")
                logger.info(cfn_delete_response)
                waitForCFN = False
            except botocore.exceptions.ClientError as error:
                logger.warning(error.response['Error']['Message'])
                return (error.response['Error']['Message'])
        #Stack is in a non-ready but health state, we wait
        elif cfnAction in ['UPDATE_IN_PROGRESS','CREATE_IN_PROGRESS','UPDATE_COMPLETE_CLEANUP_IN_PROGRESS']:
            #Stack is in progress from being created or updated, wait until the stack is steady before we delete
            logger.debug (cfnAction)
            time.sleep(5)
        #Stack is in a bad state, we won't be able to proceed so exit
        else:
            logger.warning("Stack Failed to deploy")
            logger.warning(cfn_response)
            waitForCFN = False
            return("StackFailure")
      #If the Stack doesn't exist, create it
    
