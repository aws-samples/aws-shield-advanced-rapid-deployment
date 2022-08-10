import json, boto3, random, os, time, botocore, logging, uuid

logger = logging.getLogger('hc')
logger.setLevel('DEBUG')

cfn_client = boto3.client('cloudformation')

CodeS3Bucket = os.environ['CodeS3Bucket']

def cfn_stack_manage(cfnParameters, stackSuffix, templateURL):

    cfnStackName = ("HealthChecks-" + stackSuffix).replace("/","-")
    print ("Stack Name: " + cfnStackName)
    clientRequestToken = str(uuid.uuid1())
    calculatedHCId = None
    waitForCFN = True
    timeKeeper = 0
    cfnAction = ""
    cfnEvaluate = True
    #while waitForCFN:
    #This returns an error if the stack with the asked name does not exist.  If this is the case, we are updating
    try:
      cfn_response = cfn_client.describe_stacks(
        StackName=cfnStackName)['Stacks'][0]
      logger.debug("cfn_response")
      logger.debug(cfn_response)
      cfnAction = cfn_response['StackStatus']
      counter = 0
      while cfnAction != 'CREATE_COMPLETE' and counter < 10:
          time.sleep(6)
          cfn_response = cfn_client.describe_stacks(
              StackName='FinalCloudFormationStack')['Stacks'][0]
          cfnAction = cfn_response['StackStatus']
          print(cfnAction)
          counter += 1
          print (counter)
      print(cfnAction)
    except botocore.exceptions.ClientError as error:
      if error.response['Error']['Message'] == "Stack with id " + cfnStackName + " does not exist":
        
        cfnAction = "NeedToCreate"
      else:
        logger.error(error.response['Error'])
        return (error.response['Error'])
    #In Evaluation and stack doesn't already exist, start stack create
    if cfnEvaluate == True and cfnAction == "NeedToCreate":
      try:
        logger.debug("NeedToCreate")
        stackStatus = cfn_client.create_stack(
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
        if error.response['Error']['Message'] == 'No updates are to be performed.':
          logger.info("No CFN Update needed")
          return
        else:
          logger.error(error.response['Error'])
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
    return()
