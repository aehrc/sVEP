import json
import os
import subprocess

import boto3

from api_response import bad_request, bundle_response
import chrom_matching


# AWS clients and resources
s3 = boto3.resource('s3')
sns = boto3.client('sns')

# Environment variables
SVEP_TEMP = os.environ['SVEP_TEMP']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
QUERY_VCF_EXTENDED_SNS_TOPIC_ARN = os.environ['QUERY_VCF_EXTENDED_SNS_TOPIC_ARN']
QUERY_VCF_SUBMIT_SNS_TOPIC_ARN = os.environ['QUERY_VCF_SUBMIT_SNS_TOPIC_ARN']
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'

MILLISECONDS_BEFORE_SPLIT = 15000
MILLISECONDS_BEFORE_SECOND_SPLIT = 8000
SLICE_SIZE_MBP = 5
RECORDS_PER_SAMPLE = 700
BATCH_CHUNK_SIZE = 10
PAYLOAD_SIZE = 260000
REGIONS = chrom_matching.get_regions(SLICE_SIZE_MBP)


class Timer:
    def __init__(self, context):
        self.milliseconds_left = context.get_remaining_time_in_millis

    def time_for_first_split(self):
        return self.milliseconds_left() <= MILLISECONDS_BEFORE_SPLIT

    def time_for_second_split(self):
        return self.milliseconds_left() <= MILLISECONDS_BEFORE_SECOND_SPLIT


def get_translated_regions(location):
    vcf_chromosomes = chrom_matching.get_vcf_chromosomes(location)
    vcf_regions = []
    for target_chromosome, region_list in REGIONS.items():
        chromosome = chrom_matching.get_matching_chromosome(vcf_chromosomes,
                                                            target_chromosome)
        if not chromosome:
            continue
        vcf_regions += [
            f'{chromosome}:{region}'
            for region in region_list
        ]
    return vcf_regions


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
            tot_size = len(json.dumps(remaining_coords,
                                      separators=(',', ':'))) + 1
            if tot_size < PAYLOAD_SIZE:
                sns_publish(QUERY_VCF_SUBMIT_SNS_TOPIC_ARN, {
                    'coords': remaining_coords,
                    'requestID': request_id,
                    'batchID': batch_id,
                    'lastBatch': last_batch,
                })
            else:
                # Remaining coords are still too big for SNS to handle.
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
    event_body = event.get('body')
    if not event_body:
        return bad_request("No body sent with request.")
    try:
        body_dict = json.loads(event_body)
        request_id = event['requestContext']['requestId']
        location = body_dict['location']
        vcf_regions = get_translated_regions(location)
    except ValueError:
        return bad_request("Error parsing request body, Expected JSON.")

    print(vcf_regions)
    final_data = len(vcf_regions) - 1
    for index, region in enumerate(vcf_regions):
        if timer.time_for_first_split():
            new_regions = vcf_regions[index:]
            print(f"New Regions {new_regions}")
            # Publish SNS for itself!
            sns_publish(QUERY_VCF_EXTENDED_SNS_TOPIC_ARN, {
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
    return bundle_response(200, "Process started")
