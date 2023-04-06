import json
import os
import time

import boto3


# AWS clients and resources
s3 = boto3.client('s3')
sns = boto3.client('sns')

# Environment variables
SVEP_TEMP = os.environ['SVEP_TEMP']
CONCAT_SNS_TOPIC_ARN = os.environ['CONCAT_SNS_TOPIC_ARN']
CREATEPAGES_SNS_TOPIC_ARN = os.environ['CREATEPAGES_SNS_TOPIC_ARN']
SVEP_REGIONS = os.environ['SVEP_REGIONS']
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'


def publish_result(api_id, batch_id):
    pre = f'{api_id}_{batch_id}'
    response = s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=pre)
    if len(response['Contents']) == 2:
        page_num = 0
        paginator = s3.get_paginator('list_objects_v2')
        # Change later on
        operation_parameters = {
            'Bucket': SVEP_REGIONS,
            'Prefix': api_id,
            'PaginationConfig': {
                'PageSize': 600
            }
        }
        page_iterator = paginator.paginate(**operation_parameters)
        message = {
            'APIid': api_id,
            'prefix': f'{api_id}_page',
        }
        for page in page_iterator:
            page_contents = page['Contents']
            page_keys = [d['Key'] for d in page_contents]
            page_num += 1
            message.update({
                'pageKeys': page_keys,
                'pageNum': page_num,
            })
            if 'NextContinuationToken' in page:
                message['lastPage'] = 0
            else:
                print("last page")
                print(page_num)
                message['lastPage'] = 1
            sns_publish(CREATEPAGES_SNS_TOPIC_ARN, message)
        print("Done sending to CREATEPAGES")
    else:
        print("last BatchID doesnt exist yet- resending to concat")
        resend_to_concat(api_id, batch_id)


def query_dataset(api_id, batch_id):
    objs = s3.list_objects(Bucket=SVEP_TEMP)
    if 'Contents' in objs:
        print("resending for concat")
        resend_to_concat(api_id, batch_id)
    else:
        publish_result(api_id, batch_id)


# TODO: change this to a separate low-memory function
def resend_to_concat(api_id, batch_id):
    time.sleep(5)  # Just to reduce log message spam
    message = {
        'APIid': api_id,
        'lastBatchID': batch_id,
    }
    sns_publish(CONCAT_SNS_TOPIC_ARN, message)
    # We end here so this environment is available to immediately pick
    # up the published message.


def sns_publish(topic_arn, message):
    kwargs = {
        'TopicArn': topic_arn,
        'Message': json.dumps(message),
    }
    print(f"Publishing to SNS: {json.dumps(kwargs)}")
    sns.publish(**kwargs)


def lambda_handler(event, _):
    print(f"Event Received: {json.dumps(event)}")
    message = json.loads(event['Records'][0]['Sns']['Message'])
    api_id = message['APIid']
    batch_id = message['lastBatchID']
    query_dataset(api_id, batch_id)
