import os
import shutil
import json
import math

import boto3


# AWS clients and resources
s3 = boto3.resource('s3')
sns = boto3.client('sns')

MAX_PRINT_LENGTH = 1024
MAX_SNS_EVENT_PRINT_LENGTH = 2048


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


def _truncate_string(string, max_length=MAX_PRINT_LENGTH):
    length = len(string)

    if (max_length is None) or (length <= max_length):
        return string

    excess_bytes = length - max_length
    # Excess bytes + 9 for the smallest possible placeholder
    min_removed = excess_bytes + 9
    placeholder_chars = 8 + math.ceil(math.log(min_removed, 10))
    removed_chars = excess_bytes + placeholder_chars
    while True:
        placeholder = f'<{removed_chars} bytes>'
        # Handle edge cases where the placeholder gets larger
        # when characters are removed.
        total_reduction = removed_chars - len(placeholder)
        if total_reduction < excess_bytes:
            removed_chars += 1
        else:
            break
    if removed_chars > length:
        # Handle edge cases where the placeholder is larger than
        # maximum length. In this case, just truncate the string.
        return string[:max_length]
    snip_start = (length - removed_chars) // 2
    snip_end = snip_start + removed_chars
    # Cut out the middle of the string and replace it with the
    # placeholder.
    return f"{string[:snip_start]}{placeholder}{string[snip_end:]}"


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


def print_event(event, max_length=MAX_PRINT_LENGTH):
    truncated_print(f"Event Received: {json.dumps(event)}", max_length)


def get_sns_event(event, max_length=MAX_SNS_EVENT_PRINT_LENGTH):
    print_event(event, max_length)
    return json.loads(event['Records'][0]['Sns']['Message'])


def sns_publish(topic_arn, message, max_length=MAX_PRINT_LENGTH):
    kwargs = {
        'TopicArn': topic_arn,
        'Message': json.dumps(message, separators=(',', ':')),
    }
    truncated_print(f"Publishing to SNS: {json.dumps(kwargs)}", max_length)
    sns.publish(**kwargs)


def truncated_print(string, max_length=MAX_PRINT_LENGTH):
    if max_length is not None:
        string = _truncate_string(string, max_length)
        assert len(string) <= max_length
    print(string)
