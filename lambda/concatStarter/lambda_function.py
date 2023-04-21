import os
import time

import boto3

from lambda_utils import get_sns_event, sns_publish


# AWS clients and resources
s3 = boto3.client('s3')

# Environment variables
CONCAT_SNS_TOPIC_ARN = os.environ['CONCAT_SNS_TOPIC_ARN']
CONCAT_STARTER_SNS_TOPIC_ARN = os.environ['CONCAT_STARTER_SNS_TOPIC_ARN']
LIST_INTERVAL = 5
MAX_WAIT_TIME = 8 * 60 * 60  # 8 hours
SVEP_REGIONS = os.environ['SVEP_REGIONS']
SVEP_TEMP = os.environ['SVEP_TEMP']


def ready_for_concat(api_id, batch_id):
    objs = s3.list_objects(Bucket=SVEP_TEMP, Prefix=api_id)
    if 'Contents' not in objs:
        pre = f'{api_id}_{batch_id}'
        # TODO: We shouldn't need this if all temp files are created and
        #       deleted properly
        response = s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=pre)
        if len(response['Contents']) == 2:
            return True
        print("No temporary files, but batch is not yet complete.")
    return False


def wait(api_id, batch_id, time_started):
    time_waited = time.time() - time_started
    if time_waited >= MAX_WAIT_TIME:
        print(f"Waited {time_waited} seconds. Giving up.")
        return
    time.sleep(LIST_INTERVAL)
    message = {
        'APIid': api_id,
        'lastBatchID': batch_id,
        'timeStarted': time_started,
    }
    sns_publish(CONCAT_STARTER_SNS_TOPIC_ARN, message)
    # We end here so this environment is available to immediately
    # pick up the published message.


def lambda_handler(event, _):
    message = get_sns_event(event)
    api_id = message['APIid']
    batch_id = message['lastBatchID']
    time_started = message.get('timeStarted', time.time())
    if ready_for_concat(api_id, batch_id):
        sns_publish(CONCAT_SNS_TOPIC_ARN, {
            'APIid': api_id,
        })
    else:
        wait(api_id, batch_id, time_started)
