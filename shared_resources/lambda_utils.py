import os
import shutil
import json
import math

import boto3


# AWS clients and resources
s3 = boto3.resource('s3')
sns = boto3.client('sns')

# Optional environment variables
SVEP_TEMP = os.environ.get('SVEP_TEMP')

MAX_PRINT_LENGTH = 1024
MAX_SNS_EVENT_PRINT_LENGTH = 2048
TEMP_FILE_FIELD = 'tempFileName'


class Timer:
    def __init__(self, context, buffer_time):
        self.context = context
        self.buffer_time = buffer_time

    def out_of_time(self):
        return self.context.get_remaining_time_in_millis() <= self.buffer_time


class Orchestrator:
    def __init__(self, event):
        self.message = get_sns_event(event)
        self.temp_file_name = self.message[TEMP_FILE_FIELD]
        # A flag to ensure that the temp file is deleted at the end of
        # the function.
        self.completed = False

    def __del__(self):
        assert self.completed, "Must call mark_completed at end of function."

    def mark_completed(self):
        print(f"Deleting file: {self.temp_file_name}")
        s3.Object(SVEP_TEMP, self.temp_file_name).delete()
        self.completed = True


def _get_function_name_from_arn(arn):
    return arn.split(':')[-1]


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


def download_vcf(bucket, vcf):
    keys = [
        vcf,
        f'{vcf}.tbi',
    ]
    for key in keys:
        local_file_name = f'/tmp/{key}'
        s3.Bucket(bucket).download_file(key, local_file_name)


def _create_temp_file(filename):
    print(f"Creating file: {filename}")
    s3.Object(SVEP_TEMP, filename).put(Body=b'')


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


def start_function(topic_arn, base_filename, message, resend=False,
                   max_length=MAX_PRINT_LENGTH):
    assert TEMP_FILE_FIELD not in message
    function_name = _get_function_name_from_arn(topic_arn)
    if resend:
        base_name, old_index = base_filename.rsplit(function_name, 1)
        old_index = old_index or 0  # Account for empty string
        filename = f'{base_name}{function_name}{int(old_index) + 1}'
    else:
        filename = f'{base_filename}_{function_name}'
    message[TEMP_FILE_FIELD] = filename
    _create_temp_file(filename)
    sns_publish(topic_arn, message, max_length)


def truncated_print(string, max_length=MAX_PRINT_LENGTH):
    if max_length is not None:
        string = _truncate_string(string, max_length)
        assert len(string) <= max_length
    print(string)
