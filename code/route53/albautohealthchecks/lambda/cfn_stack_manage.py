import json, boto3, random, os, time, botocore, logging, uuid

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

cfn_client = boto3.client('cloudformation')
shield_client = boto3.client('shield')
hc_regions = os.environ['HC_Regions'].split(',')
CodeS3Bucket = os.environ['CodeS3Bucket']
healthCheckKey = os.environ['HealthCheckKey']
templateURL = "https://" + CodeS3Bucket + ".s3.amazonaws.com/" + healthCheckKey


def cfn_stack_manage(cfnParameters, stackPrefix, shieldProtections):
    cfnStackName = stackPrefix + "-HealthChecks"
    clientRequestToken = str(uuid.uuid1())
    calculatedHCId = None
    waitForCFN = True
    timeKeeper = 0
    cfnAction = ""
    cfnEvaluate = True
    while waitForCFN:
      #This returns an error if the stack with the asked name does not exist.  If this is the case, we are updating
      try:
        cfn_response = cfn_client.describe_stacks(
          StackName=cfnStackName)['Stacks'][0]
        logger.debug("cfn_response")
        logger.debug(cfn_response)
        cfnAction = cfn_response['StackStatus']
      except botocore.exceptions.ClientError as error:
        if error.response['Error']['Message'] == "Stack with id " + cfnStackName + " does not exist":
          cfnAction = "NeedToCreate"
        else:
          logger.error(error.response['Error'])
          return (error.response['Error'])
      #In Evaluation and stack doesn't already exist, start stack create
      if cfnEvaluate == True and cfnAction == "NeedToCreate":
        try:
          cfn_client.create_stack(
              StackName=cfnStackName,
              TemplateURL=templateURL,
              Parameters=cfnParameters,
              TimeoutInMinutes=2,
              OnFailure='DELETE',
              ClientRequestToken=clientRequestToken
          )
          cfnAction = 'deploying'
          cfnEvaluate = False
        except botocore.exceptions.ClientError as error:
          logger.error(error.response['Error'])
          return(error.response['Error'])
      #Stack is steady and ready to be updated, start stack update
      elif cfnEvaluate == True and (cfnAction in ['UPDATE_COMPLETE','CREATE_COMPLETE','UPDATE_ROLLBACK_COMPLETE']):
        logger.info("Stack already exists and in steady state, update the stack")
        try:
          cfn_client.update_stack(
            StackName=cfnStackName,
            TemplateURL=templateURL,
            Parameters=cfnParameters,
            ClientRequestToken=clientRequestToken
            )
          cfnEvaluate = False
        except botocore.exceptions.ClientError as error:
          logger.warning(error.response['Error'])
          return(error.response['Error'])
      #Stack is still creating or updating, wait
      elif cfnAction in ['UPDATE_IN_PROGRESS','CREATE_IN_PROGRESS','UPDATE_COMPLETE_CLEANUP_IN_PROGRESS']:
        logger.debug (cfnAction)
      #Stack finished creating or updating and is done, proceed
      elif cfnEvaluate == False and cfnAction in ['UPDATE_COMPLETE','CREATE_COMPLETE']:
        waitForCFN = False
        #The Stack output is the calcualated ID, capture that
        calculatedHCId = cfn_response['Outputs'][0]['OutputValue']
      #Stack Had some type of issue
      else:
        logger.warning("Stack Failed to deploy")
        logger.warning(cfn_response)
        return("StackFailure")
      time.sleep(5)
    for shieldProtection in shieldProtections:
      if 'HealthCheckIds' in shieldProtection['Protection']:
        #If there is an existing associated health check and it is different that the stack return, remove that association
        try:
            logger.debug("Removing existing HC: " + shieldProtection['Protection']['HealthCheckIds'][0])
            shield_response = shield_client.disassociate_health_check(
                ProtectionId=shieldProtection['Protection']['Id'],
                HealthCheckArn='arn:aws:route53:::healthcheck/' + shieldProtection['Protection']['HealthCheckIds'][0]
            )
            logger.debug(shield_response)
        except botocore.exceptions.ClientError as error:
          logger.info(error.response['Error']['Message'])
      try:
        logger.debug("Associate Health Check: " + str(calculatedHCId))
        response = shield_client.associate_health_check(
                ProtectionId=shieldProtection['Protection']['Id'],
                HealthCheckArn='arn:aws:route53:::healthcheck/' + str(calculatedHCId)
            )
      except botocore.exceptions.ClientError as error:
        logger.error(error.response['Error']['Message'])
        raise
      return()