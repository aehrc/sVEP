import json
import os
import subprocess

import lambda_utils


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
lambda_utils.download_vcf(BUCKET_NAME, REFERENCE_GENOME)


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
            lambda_utils.delete_temp_file(SVEP_TEMP, api_id, batch_id)


def send_data_to_plugins(api_id, results, counter, batch_id, last_batch):
    unique_batch_id = f'{batch_id}_{counter}'
    print(unique_batch_id)
    for topic in TOPICS:
        temp_file_name = lambda_utils.create_temp_file(SVEP_TEMP, api_id,
                                                       unique_batch_id, topic)
        lambda_utils.sns_publish(topic, {
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
    lambda_utils.sns_publish(QUERY_GTF_SNS_TOPIC_ARN, {
        'coords': remaining_coords,
        'APIid': api_id,
        'batchID': unique_batch_id,
        'lastBatch': last_batch,
    })
    lambda_utils.create_temp_file(SVEP_TEMP, api_id, unique_batch_id)
    lambda_utils.delete_temp_file(SVEP_TEMP, api_id, batch_id)


def lambda_handler(event, context):
    message = lambda_utils.get_sns_event(event)
    timer = lambda_utils.Timer(context, MILLISECONDS_BEFORE_SPLIT)
    coords = message['coords']
    api_id = message['APIid']
    batch_id = message['batchID']
    last_batch = message['lastBatch']
    overlap_feature(coords, api_id, batch_id, last_batch, timer)
