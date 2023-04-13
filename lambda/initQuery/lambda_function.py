import json
import os

from api_response import bad_request, bundle_response
import chrom_matching
from lambda_utils import print_event, sns_publish


# Environment variables
QUERY_VCF_SNS_TOPIC_ARN = os.environ['QUERY_VCF_SNS_TOPIC_ARN']
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'

SLICE_SIZE_MBP = 5
REGIONS = chrom_matching.get_regions(SLICE_SIZE_MBP)


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


def lambda_handler(event, _):
    print_event(event)
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
    sns_publish(QUERY_VCF_SNS_TOPIC_ARN, {
        'regions': vcf_regions,
        'requestID': request_id,
        'location': location,
    })
    return bundle_response(200, "Process started")
