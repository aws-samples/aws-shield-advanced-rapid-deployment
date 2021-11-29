import sys
sys.path.insert(0,'./fms/enableConfigure/lambda')
import boto3
import os
import cfnresponse
import logging

log = logging.getLogger('fms_admin')
log.setLevel('INFO')

fms_client = boto3.client('fms')

admin_account_id = os.environ['AdminAccountId']

def associate_admin_account(admin_account_id):
    log.info(f'attempting to set Firewall Manager administrator account to {admin_account_id}')
    fms_client.associate_admin_account(AdminAccount=admin_account_id)
    log.info(f'finished setting Firewall Manager administrator account to {admin_account_id}')

def lambda_handler(event, context):
    log.info(event)
    if event.get('RequestType', None) == 'Create':
        try:
            associate_admin_account(admin_account_id)
            cfnresponse.send(event, context, cfnresponse.SUCCESS, dict(), 'AssociateFMSAdminAccountSucceesful')
        except Exception as e:
            log.error(e)
            cfnresponse.send(event, context, cfnresponse.FAILED, dict(), 'AssociateFMSAdminAccountFailed')
    else:
        cfnresponse.send(event, context, cfnresponse.SUCCESS, dict(), 'GracefulContinue')
