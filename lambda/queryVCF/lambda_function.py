import os
import subprocess

from lambda_utils import create_temp_file, get_sns_event, sns_publish, Timer


# Environment variables
SVEP_TEMP = os.environ['SVEP_TEMP']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
QUERY_VCF_SNS_TOPIC_ARN = os.environ['QUERY_VCF_SNS_TOPIC_ARN']
QUERY_VCF_SUBMIT_SNS_TOPIC_ARN = os.environ['QUERY_VCF_SUBMIT_SNS_TOPIC_ARN']
SLICE_SIZE_MBP = int(os.environ['SLICE_SIZE_MBP'])
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'

MILLISECONDS_BEFORE_SPLIT = 15000
MILLISECONDS_BEFORE_SECOND_SPLIT = 6000
RECORDS_PER_SAMPLE = 700
BATCH_CHUNK_SIZE = 10
PAYLOAD_SIZE = 260000


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


def submit_query_gtf(query_process, request_id, region_id, last_batch,
                     timer):
    regions_list = query_process.stdout.read().splitlines()
    total_coords = [
        regions_list[x:x+RECORDS_PER_SAMPLE]
        for x in range(0, len(regions_list), RECORDS_PER_SAMPLE)
    ]

    final_data = len(total_coords) - 1
    for idx in range(len(total_coords)):
        is_last = (idx == final_data) and last_batch
        batch_id = f'{region_id}_{idx}'
        if is_last:
            print("last Batch")
        if timer.out_of_time():
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
            create_temp_file(SVEP_TEMP, request_id, batch_id)
            sns_publish(QUERY_GTF_SNS_TOPIC_ARN, {
                'coords': total_coords[idx],
                'APIid': request_id,
                'batchID': batch_id,
                'lastBatch': is_last,
            })


def lambda_handler(event, context):
    message = get_sns_event(event)
    first_timer = Timer(context, MILLISECONDS_BEFORE_SPLIT)
    second_timer = Timer(context, MILLISECONDS_BEFORE_SECOND_SPLIT)
    vcf_regions = message['regions']
    request_id = message['requestID']
    location = message['location']
    final_data = len(vcf_regions) - 1
    for index, region in enumerate(vcf_regions):
        if first_timer.out_of_time():
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
                             int(index == final_data), second_timer)
