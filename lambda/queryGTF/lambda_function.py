import json
import os
import subprocess

import boto3


# AWS clients and resources
sns = boto3.client('sns')
s3 = boto3.resource('s3')

# Environment variables
SVEP_TEMP = os.environ['SVEP_TEMP']
REFERENCE_GENOME = os.environ['REFERENCE_GENOME']
PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN = os.environ['PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN']
PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN = os.environ['PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'
TOPICS = [
    PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN,
    PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN,
]

BUCKET_NAME = 'svep'
MILLISECONDS_BEFORE_SPLIT = 4000
PAYLOAD_SIZE = 260000

# Download reference genome and index
KEYS = [
    REFERENCE_GENOME,
    f'{REFERENCE_GENOME}.tbi',
]
for key in KEYS:
    local_file_name = f'/tmp/{key}'
    s3.Bucket(BUCKET_NAME).download_file(key, local_file_name)


class Timer:
    def __init__(self, context):
        self.milliseconds_left = context.get_remaining_time_in_millis

    def out_of_time(self):
        return self.milliseconds_left() <= MILLISECONDS_BEFORE_SPLIT


def create_temp_file(filename):
    print(f"File created is - {filename}")
    s3.Object(SVEP_TEMP, filename).put(Body=b'')


def delete_temp_file(api_id, batch_id):
    filename = f'{api_id}_{batch_id}'
    print(f"File deleting - {filename}")
    s3.Object(SVEP_TEMP, filename).delete()


def overlap_feature(all_coords, api_id, batch_id, last_batch, timer):
    results = []
    final_data = len(all_coords) - 1
    tot_size = 0
    counter = 0
    for idx, coord in enumerate(all_coords):
        chrom, pos, ref, alt = coord.split('\t')
        loc = f'{chrom}:{pos}-{pos}'
        local_file = f'/tmp/{REFERENCE_GENOME}'
        args = [
            'tabix',
            local_file,
            loc
        ]
        query_process = subprocess.Popen(args, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         cwd='/tmp', encoding='ascii')
        main_data = query_process.stdout.read().rstrip('\n').split('\n')
        data = {
            'chrom': chrom,
            'pos': pos,
            'ref': ref,
            'alt': alt,
            'data': main_data,
        }
        cur_size = len(json.dumps(data, separators=(',', ':'))) + 1
        tot_size += cur_size
        if tot_size < PAYLOAD_SIZE:
            results.append(data)
            if timer.out_of_time():
                # should only be executed in very few cases.
                counter += 1
                send_data_to_plugins(api_id, results, counter, batch_id, 0)
                send_data_to_self(api_id, all_coords[idx:], batch_id, counter,
                                  last_batch)
                break
        else:
            counter += 1
            send_data_to_plugins(api_id, results, counter, batch_id, 0)
            if timer.out_of_time():
                send_data_to_self(api_id, all_coords[idx:], batch_id, counter,
                                  last_batch)
                break
            else:
                results = [data]
                tot_size = cur_size

        if idx == final_data:
            counter += 1
            # TODO: Don't send this if we just sent because results was
            #   full. Also make sure that previous message included
            #   lastBatch=last_batch.
            send_data_to_plugins(api_id, results, counter, batch_id,
                                 last_batch)
            delete_temp_file(api_id, batch_id)


def send_data_to_plugins(api_id, results, counter, batch_id, last_batch):
    unique_batch_id = f'{batch_id}_{counter}'
    print(unique_batch_id)
    for topic in TOPICS:
        temp_file_name = f'{api_id}_{unique_batch_id}_{topic}'
        create_temp_file(temp_file_name)
        sns_publish(topic, {
            'snsData': results,
            'APIid': api_id,
            'batchID': unique_batch_id,
            'tempFileName': temp_file_name,
            # Only one plugin, currently updownstream, should act on the
            # lastBatch value.
            'lastBatch': last_batch,
        })


def send_data_to_self(api_id, remaining_coords, batch_id, counter, last_batch):
    unique_batch_id = f'{batch_id}_GTF{counter}'
    print("Less Time remaining - call itself.")
    sns_publish(QUERY_GTF_SNS_TOPIC_ARN, {
        'coords': remaining_coords,
        'APIid': api_id,
        'batchID': unique_batch_id,
        'lastBatch': last_batch,
    })
    create_temp_file(f'{api_id}_{unique_batch_id}')
    delete_temp_file(api_id, batch_id)


def sns_publish(topic_arn, message):
    kwargs = {
        'TopicArn': topic_arn,
        'Message': json.dumps(message, separators=(',', ':')),
    }
    print(f"Publishing to SNS: {json.dumps(kwargs)}")
    sns.publish(**kwargs)


def lambda_handler(event, context):
    print(f"Event Received: {json.dumps(event)}")
    timer = Timer(context)
    message = json.loads(event['Records'][0]['Sns']['Message'])
    coords = message['coords']
    api_id = message['APIid']
    batch_id = message['batchID']
    last_batch = message['lastBatch']
    overlap_feature(coords, api_id, batch_id, last_batch, timer)
