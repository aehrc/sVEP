import os
import subprocess

from lambda_utils import Orchestrator, start_function, Timer


# Environment variables
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


def submit_query_gtf(query_process, base_id, timer):
    regions_list = query_process.stdout.read().splitlines()
    total_coords = [
        regions_list[x:x+RECORDS_PER_SAMPLE]
        for x in range(0, len(regions_list), RECORDS_PER_SAMPLE)
    ]

    for idx in range(len(total_coords)):
        idx_base_id = f'{base_id}_{idx}'
        if timer.out_of_time():
            # Call self with remaining data
            remaining_coords = total_coords[idx:]
            print(f"remaining coords length {len(remaining_coords)}")
            # Since coords are generally similar size because it's
            # made of chr, loc, ref, alt - we know 10 batches of 700
            # records can be handled by SNS
            for i in range(0, len(remaining_coords), BATCH_CHUNK_SIZE):
                start_function(
                    topic_arn=QUERY_VCF_SUBMIT_SNS_TOPIC_ARN,
                    base_filename=f'{idx_base_id}_{i}',
                    message={
                        'coords': remaining_coords[i:i+BATCH_CHUNK_SIZE],
                    },
                )
            break
        else:
            start_function(
                topic_arn=QUERY_GTF_SNS_TOPIC_ARN,
                base_filename=idx_base_id,
                message={
                    'coords': total_coords[idx],
                },
            )


def lambda_handler(event, context):
    orchestrator = Orchestrator(event)
    message = orchestrator.message
    first_timer = Timer(context, MILLISECONDS_BEFORE_SPLIT)
    second_timer = Timer(context, MILLISECONDS_BEFORE_SECOND_SPLIT)
    vcf_regions = message['regions']
    location = message['location']
    base_id = orchestrator.temp_file_name
    for index, region in enumerate(vcf_regions):
        if first_timer.out_of_time():
            new_regions = vcf_regions[index:]
            print(f"New Regions {new_regions}")
            # Publish SNS for itself!
            start_function(
                topic_arn=QUERY_VCF_SNS_TOPIC_ARN,
                base_filename=base_id,
                message={
                    'regions': new_regions,
                    'location': location,
                },
                resend=True,
            )
            break
        else:
            chrom, start_str = region.split(':')
            region_base_id = f'{base_id}_{chrom}_{start_str}'
            start = round(1000000*float(start_str) + 1)
            end = start + round(1000000*SLICE_SIZE_MBP - 1)
            query_process = get_query_process(location, chrom, start, end)
            submit_query_gtf(query_process, region_base_id, second_timer)
    orchestrator.mark_completed()
