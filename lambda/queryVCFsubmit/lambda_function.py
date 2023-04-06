import json
import os

import boto3


# AWS clients and resources
s3 = boto3.resource('s3')
sns = boto3.client('sns')

# Environment variables
SVEP_TEMP = os.environ['SVEP_TEMP']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'


def create_temp_file(api_id, batch_id):
    filename = f'{api_id}_{batch_id}'
    s3.Object(SVEP_TEMP, filename).put(Body=b'')


def sns_publish(topic_arn, message):
    kwargs = {
        'TopicArn': topic_arn,
        'Message': json.dumps(message, separators=(',', ':')),
    }
    print(f"Publishing to SNS: {json.dumps(kwargs)}")
    sns.publish(**kwargs)


def lambda_handler(event, _):
    print('Event Received: {}'.format(json.dumps(event)))
    message = json.loads(event['Records'][0]['Sns']['Message'])
    total_coords = message['coords']
    request_id = message['requestID']
    batch_id = message['batchID']
    last_batch = message['lastBatch']
    print(total_coords)
    print(batch_id)
    print(f"length = {len(total_coords)}")
    final_data = len(total_coords) - 1
    for idx in range(len(total_coords)):
        is_last = (idx == final_data) and last_batch
        new_batch_id = f'{batch_id}_{str(idx)}'
        print(new_batch_id)
        create_temp_file(request_id, new_batch_id)
        sns_publish(QUERY_GTF_SNS_TOPIC_ARN, {
            'coords': total_coords[idx],
            'APIid': request_id,
            'batchID': new_batch_id,
            'lastBatch': is_last,
        })
