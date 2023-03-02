import datetime
import json
import os
import subprocess
import time
import boto3

from api_response import bad_request, bundle_response, missing_parameter
from chrom_matching import CHROMOSOME_LENGTHS_MBP, get_vcf_chromosomes, get_matching_chromosome
MILLISECONDS_BEFORE_SPLIT = 15000
SLICE_SIZE_MBP = 100
RECORDS_PER_SAMPLE = 100
PAYLOAD_SIZE = 262000
DATASETS_TABLE_NAME = os.environ['DATASETS_TABLE']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
QUERY_VCF_EXTENDED_SNS_TOPIC_ARN = os.environ['QUERY_VCF_EXTENDED_SNS_TOPIC_ARN']
CONCAT_SNS_TOPIC_ARN = os.environ['CONCAT_SNS_TOPIC_ARN']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']
sns = boto3.client('sns')
dynamodb = boto3.client('dynamodb')




regions = {}
for chrom, size in CHROMOSOME_LENGTHS_MBP.items():
    chrom_regions = []
    start = 0
    while start < size:
        chrom_regions.append(start)
        start += SLICE_SIZE_MBP
    regions[chrom] = chrom_regions

def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size

def get_translated_regions(location):
    vcf_chromosomes = get_vcf_chromosomes(location)
    vcf_regions = []
    for target_chromosome, region_list in regions.items():
        chromosome = get_matching_chromosome(vcf_chromosomes, target_chromosome)
        if not chromosome:
            continue
        vcf_regions += ['{}:{}'.format(chromosome, region)
                        for region in region_list]
    return vcf_regions
def get_regions(location, chrom, start, end):
    test = time.time()
    args = [
        'bcftools', 'query',
        '--regions', '{chrom}:{start}-{end}'.format(chrom=chrom, start=start, end=end),
        '--format', '%CHROM\t%POS\t%REF\t%ALT\n',
        location
    ]
    query_process = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.PIPE, cwd='/tmp',encoding='ascii')
    #print(args)
    #print(query_process.stderr.read())
    print("get regions time = ",(time.time() - test)*1000)
    return query_process

def get_regions_and_variants(location, chrom, start, end, time_assigned):
    regions_process = get_regions(location,chrom, start, end)
    regions_list = regions_process.stdout.read().splitlines()
    all_coords = [l.split('\t')[0]+"\t"+l.split('\t')[1] for l in regions_list]
    all_changes = [l.split('\t')[2]+"\t"+l.split('\t')[3] for l in regions_list]
    return all_coords,all_changes

def putDataset(APIid,batchID):
    '''item = {
        'APIid':APIid,
        'batchID':batchID,
        'count':0
        }
    kwargs = {
        'TableName': DATASETS_TABLE_NAME,
        'Item': item,
    }'''
    kwargs = {
        'TableName': DATASETS_TABLE_NAME,
        'Key': {
            'APIid': {
                'S': APIid,
            },
        },
        'UpdateExpression': 'ADD batchID :b, filesCount :c ',
        'ExpressionAttributeValues': {':b': { 'SS' : [batchID]}, ':c' :{'N':'0'} },
    }
    print('Updating item: {}'.format(json.dumps(kwargs)))
    dynamodb.update_item(**kwargs)


def submitQueryGTF(total_coords,total_changes, requestID, regionID):
    kwargs = {
        'TopicArn': QUERY_GTF_SNS_TOPIC_ARN,
    }

    print("length = ",len(total_coords) )
    for idx in range(len(total_coords)):
        batchID = regionID+"_"+str(idx)
        print(batchID)
        putDataset(requestID,batchID)
        kwargs['Message'] = json.dumps({
            'coords':total_coords[idx],
            'changes':total_changes[idx],
            'APIid':requestID,
            'batchID':batchID
        })
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        print('Received Response: {}'.format(json.dumps(response)))
        return(batchID)




def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    time_assigned = (context.get_remaining_time_in_millis()-MILLISECONDS_BEFORE_SPLIT)
    print("time assigned",time_assigned)
    timeStart = time.time()

    message = json.loads(event['Records'][0]['Sns']['Message'])
    vcf_regions = message['regions']
    requestID = message['requestID']
    location = message['location']


    batchID = ''
    print(vcf_regions)
    for index,region in enumerate(vcf_regions):
        if( (time.time() - timeStart)*1000 > time_assigned):
            newRegions = vcf_regions[index:]
            batchID = ''
            print("New Regions ",newRegions)
            #publish Sns for itself!
            kwargs = {
                'TopicArn': QUERY_VCF_EXTENDED_SNS_TOPIC_ARN,
            }
            kwargs['Message'] = json.dumps({'regions' : newRegions,'requestID' : requestID, 'location': location})
            print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
            response = sns.publish(**kwargs)
            print('Received Response: {}'.format(json.dumps(response)))
            break
        else:
            chrom, start_str = region.split(':')
            regionID = chrom+"_"+start_str
            start = round(1000000 * float(start_str) + 1)
            end = start + round(1000000 * SLICE_SIZE_MBP - 1)
            all_coords, all_changes = get_regions_and_variants(location, chrom, start, end, time_assigned)
            total_coords = [all_coords[x:x+RECORDS_PER_SAMPLE] for x in range(0, len(all_coords), RECORDS_PER_SAMPLE)]
            total_changes = [all_changes[x:x+RECORDS_PER_SAMPLE] for x in range(0, len(all_changes), RECORDS_PER_SAMPLE)]
            batchID = submitQueryGTF(total_coords,total_changes,requestID,regionID)
    if(batchID != ''):
        kwargs = {
            'TopicArn': CONCAT_SNS_TOPIC_ARN,
        }
        kwargs['Message'] = json.dumps({'APIid' : requestID,'lastBatchID' : batchID})
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        print('Received Response: {}'.format(json.dumps(response)))

    return bundle_response(200, "Process started")
    #return(event_body)
    #return( bundle_response(200, {   'message' : get_sample_count(event['queryStringParameters']['location'])}))
