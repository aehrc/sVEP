import os
import time

import boto3

from lambda_utils import get_sns_event, sns_publish
import s3fs


# AWS clients and resources
fs = s3fs.S3FileSystem(anon=False)
s3 = boto3.client('s3')

# Environment variables
RESULT_SUFFIX = os.environ['RESULT_SUFFIX']
SVEP_REGIONS = os.environ['SVEP_REGIONS']
SVEP_RESULTS = os.environ['SVEP_RESULTS']
CONCATPAGES_SNS_TOPIC_ARN = os.environ['CONCATPAGES_SNS_TOPIC_ARN']
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'


def publish_result(api_id, all_keys, last_file, page_num, prefix):
    start_time = time.time()
    filename = f'{api_id}{RESULT_SUFFIX}'
    file_path = f's3://{SVEP_RESULTS}/{filename}'
    response = s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=prefix)
    if len(response['Contents']) == page_num:
        paths = [
            f'{SVEP_REGIONS}/{d}'
            for d in all_keys
        ]
        fs.merge(path=file_path, filelist=paths)
        print(f"time taken = {(time.time()-start_time) * 1000}")
        print("Done concatenating")
    else:
        print("createPages failed to create one of the page")
        sns_publish(CONCATPAGES_SNS_TOPIC_ARN, {
            'APIid': api_id,
            'lastFile': last_file,
            'pageNum': page_num,
        })


def lambda_handler(event, _):
    message = get_sns_event(event)
    api_id = message['APIid']
    all_keys = message['allKeys']
    last_file = message['lastFile']
    page_num = message['pageNum']
    prefix = message['prefix']
    publish_result(api_id, all_keys, last_file, page_num, prefix)
