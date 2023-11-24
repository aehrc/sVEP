import json
import os

from api_response import bad_request, bundle_response
import chrom_matching
from lambda_utils import print_event, sns_publish, start_function


# Environment variables
CONCAT_STARTER_SNS_TOPIC_ARN = os.environ['CONCAT_STARTER_SNS_TOPIC_ARN']
QUERY_VCF_SNS_TOPIC_ARN = os.environ['QUERY_VCF_SNS_TOPIC_ARN']
RESULT_BUCKET = os.environ['SVEP_RESULTS']
RESULT_DURATION = int(os.environ['RESULT_DURATION'])
RESULT_SUFFIX = os.environ['RESULT_SUFFIX']
SLICE_SIZE_MBP = int(os.environ['SLICE_SIZE_MBP'])
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'

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
    print_event(event, max_length=None)
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
    start_function(QUERY_VCF_SNS_TOPIC_ARN, request_id, {
        'regions': vcf_regions,
        'location': location,
    })
    sns_publish(CONCAT_STARTER_SNS_TOPIC_ARN, {
        # TODO: Change all these APIid strings to requestID
        'APIid': request_id,
    })

    return bundle_response(200, {
        "Response": "Process started",
        "RequestId": request_id,
    })
