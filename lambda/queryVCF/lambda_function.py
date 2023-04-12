import json
import os
import subprocess

import boto3


# AWS clients and resources
s3 = boto3.resource('s3')
sns = boto3.client('sns')

# Environment variables
SVEP_TEMP = os.environ['SVEP_TEMP']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
QUERY_VCF_SNS_TOPIC_ARN = os.environ['QUERY_VCF_SNS_TOPIC_ARN']
QUERY_VCF_SUBMIT_SNS_TOPIC_ARN = os.environ['QUERY_VCF_SUBMIT_SNS_TOPIC_ARN']
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'

MILLISECONDS_BEFORE_SPLIT = 15000
MILLISECONDS_BEFORE_SECOND_SPLIT = 6000
SLICE_SIZE_MBP = 5  # TODO: Sync this with initQuery
RECORDS_PER_SAMPLE = 700
BATCH_CHUNK_SIZE = 10
PAYLOAD_SIZE = 260000


class Timer:
    def __init__(self, context):
        self.milliseconds_left = context.get_remaining_time_in_millis

    def time_for_first_split(self):
        return self.milliseconds_left() <= MILLISECONDS_BEFORE_SPLIT

    def time_for_second_split(self):
        return self.milliseconds_left() <= MILLISECONDS_BEFORE_SECOND_SPLIT


def get_query_process(location, chrom, start, end):
    args = [
        'bcftools', 'query',
        '--regions', f'{chrom}:{start}-{end}',
        '--format', '%CHROM\t%POS\t%REF\t%ALT\n',
        location
    ]
    return subprocess.Popen(args, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd='/tmp',
                            encoding='ascii')


def create_temp_file(api_id, batch_id):
    filename = f'{api_id}_{batch_id}'
    s3.Object(SVEP_TEMP, filename).put(Body=b'')


def submit_query_gtf(query_process, request_id, region_id, last_batch,
                     timer):
    regions_list = query_process.stdout.read().splitlines()
    total_coords = [
        regions_list[x:x+RECORDS_PER_SAMPLE]
        for x in range(0, len(regions_list), RECORDS_PER_SAMPLE)
    ]

    print(f"length = {len(total_coords)}")
    final_data = len(total_coords) - 1
    for idx in range(len(total_coords)):
        is_last = (idx == final_data) and last_batch
        batch_id = f'{region_id}_{idx}'
        if is_last:
            print("last Batch")
        if timer.time_for_second_split():
            # Call self with remaining data
            remaining_coords = total_coords[idx:]
            print(f"remaining Coords length {len(remaining_coords)}")
            # Since coords are generally similar size because it's
            # made of chr, loc, ref, alt - we know 10 batches of 700
            # records can be handled by SNS
            for i in range(0, len(remaining_coords), BATCH_CHUNK_SIZE):
                sns_publish(QUERY_VCF_SUBMIT_SNS_TOPIC_ARN, {
                    'coords': remaining_coords[i:i+BATCH_CHUNK_SIZE],
                    'requestID': request_id,
                    'batchID': f'{batch_id}_sns{i}',
                    # The choice of lastBatch is arbitrary in this
                    # case, so we'll just mark the first one as it's
                    # quicker to check.
                    'lastBatch': (i == 0) and last_batch,
                })
            break
        else:
            print(batch_id)
            create_temp_file(request_id, batch_id)
            sns_publish(QUERY_GTF_SNS_TOPIC_ARN, {
                'coords': total_coords[idx],
                'APIid': request_id,
                'batchID': batch_id,
                'lastBatch': is_last,
            })


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
    vcf_regions = message['regions']
    request_id = message['requestID']
    location = message['location']
    final_data = len(vcf_regions) - 1
    for index, region in enumerate(vcf_regions):
        if timer.time_for_first_split():
            new_regions = vcf_regions[index:]
            print(f"New Regions {new_regions}")
            # Publish SNS for itself!
            sns_publish(QUERY_VCF_SNS_TOPIC_ARN, {
                'regions': new_regions,
                'requestID': request_id,
                'location': location,
            })
            break
        else:
            chrom, start_str = region.split(':')
            region_id = f'{chrom}_{start_str}'
            start = round(1000000*float(start_str) + 1)
            end = start + round(1000000*SLICE_SIZE_MBP - 1)
            query_process = get_query_process(location, chrom, start, end)
            submit_query_gtf(query_process, request_id, region_id,
                             int(index == final_data), timer)
