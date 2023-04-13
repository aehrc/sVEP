import os
import shutil
import json

import boto3


# AWS clients and resources
s3 = boto3.resource('s3')
sns = boto3.client('sns')


class Timer:
    def __init__(self, context, buffer_time):
        self.context = context
        self.buffer_time = buffer_time

    def out_of_time(self):
        return self.context.get_remaining_time_in_millis() <= self.buffer_time


def _get_file_name(api_id, batch_id, suffix=None):
    filename = f'{api_id}_{batch_id}'
    if suffix is not None:
        filename = f'{filename}_{suffix}'
    return filename


def delete_temp_file(bucket, api_id, batch_id, suffix=None):
    filename = _get_file_name(api_id, batch_id, suffix)
    print(f"Deleting file: {filename}")
    s3.Object(bucket, filename).delete()


def download_vcf(bucket, vcf):
    keys = [
        vcf,
        f'{vcf}.tbi',
    ]
    for key in keys:
        local_file_name = f'/tmp/{key}'
        s3.Bucket(bucket).download_file(key, local_file_name)


def create_temp_file(bucket, api_id, batch_id, suffix=None):
    filename = _get_file_name(api_id, batch_id, suffix)
    print(f"Creating file: {filename}")
    s3.Object(bucket, filename).put(Body=b'')
    return filename


def clear_tmp():
    for file_name in os.listdir('/tmp'):
        file_path = f'/tmp/{file_name}'
        if os.path.isfile(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)


def print_event(event):
    print(f"Event Received: {json.dumps(event)}")


def get_sns_event(event):
    print_event(event)
    return json.loads(event['Records'][0]['Sns']['Message'])


def sns_publish(topic_arn, message):
    kwargs = {
        'TopicArn': topic_arn,
        'Message': json.dumps(message, separators=(',', ':')),
    }
    print(f"Publishing to SNS: {json.dumps(kwargs)}")
    sns.publish(**kwargs)
