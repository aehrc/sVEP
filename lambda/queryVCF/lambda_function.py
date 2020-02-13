import datetime
import json
import os
import subprocess
import time
import boto3
from api_response import bad_request, bundle_response, missing_parameter
from chrom_matching import CHROMOSOME_LENGTHS_MBP, get_vcf_chromosomes, get_matching_chromosome
#global vars
MILLISECONDS_BEFORE_SPLIT = 15000
SLICE_SIZE_MBP = 100
RECORDS_PER_SAMPLE = 700
PAYLOAD_SIZE = 262000
s3 = boto3.resource('s3')
sns = boto3.client('sns')
dynamodb = boto3.client('dynamodb')
#environ variables
SVEP_TEMP = os.environ['SVEP_TEMP']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
QUERY_VCF_EXTENDED_SNS_TOPIC_ARN = os.environ['QUERY_VCF_EXTENDED_SNS_TOPIC_ARN']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']

regions = {}
for chrom, size in CHROMOSOME_LENGTHS_MBP.items():
    chrom_regions = []
    start = 0
    while start < size:
        chrom_regions.append(start)
        start += SLICE_SIZE_MBP
    regions[chrom] = chrom_regions

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
    #print("get regions time = ",(time.time() - test)*1000)
    return query_process

def get_regions_and_variants(location, chrom, start, end, time_assigned):
    regions_process = get_regions(location,chrom, start, end)
    regions_list = regions_process.stdout.read().splitlines()
    all_coords = [l.split('\t')[0]+"\t"+l.split('\t')[1] for l in regions_list]
    all_changes = [l.split('\t')[2]+"\t"+l.split('\t')[3] for l in regions_list]
    return all_coords,all_changes

def createTempFile(APIid,batchID):
    filename = APIid+"_"+batchID
    s3.Object(SVEP_TEMP, filename).put(Body=(b""))

def submitQueryGTF(total_coords,total_changes, requestID, regionID,lastBatchID):
    kwargs = {
        'TopicArn': QUERY_GTF_SNS_TOPIC_ARN,
    }

    print("length = ",len(total_coords) )
    finalData = len(total_coords) - 1
    for idx in range(len(total_coords)):
        if((idx == finalData) and (lastBatchID == 1) ):
            batchID = regionID+"_"+str(idx)
            print(batchID)
            createTempFile(requestID,batchID)
            kwargs['Message'] = json.dumps({
                'coords':total_coords[idx],
                'changes':total_changes[idx],
                'APIid':requestID,
                'batchID':batchID,
                'lastBatchID' : lastBatchID
            })
        else:
            batchID = regionID+"_"+str(idx)
            print(batchID)
            createTempFile(requestID,batchID)
            kwargs['Message'] = json.dumps({
                'coords':total_coords[idx],
                'changes':total_changes[idx],
                'APIid':requestID,
                'batchID':batchID,
                'lastBatchID': 0
            })
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        print('Received Response: {}'.format(json.dumps(response)))
        #return(batchID)

def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    time_assigned = (context.get_remaining_time_in_millis()-MILLISECONDS_BEFORE_SPLIT)
    print("time assigned",time_assigned)
    timeStart = time.time()
    event_body = event.get('body')
    if not event_body:
            return bad_request('No body sent with request.')
    try:
        body_dict = json.loads(event_body)
        requestID = event['requestContext']['requestId']
        location = body_dict['location']
        vcf_regions = get_translated_regions(location)
    except ValueError:
        return bad_request('Error parsing request body, Expected JSON.')

    batchID = ''
    print(vcf_regions)
    finalData = len(vcf_regions) - 1
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
            if (index == finalData):
                submitQueryGTF(total_coords,total_changes,requestID,regionID,1)
            else:
                submitQueryGTF(total_coords,total_changes,requestID,regionID,0)



    '''if(batchID != ''):
        print("sending for concat")
        kwargs = {
            'TopicArn': CONCAT_SNS_TOPIC_ARN,
        }
        kwargs['Message'] = json.dumps({'APIid' : requestID,'lastBatchID' : batchID})
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        print('Received Response: {}'.format(json.dumps(response)))'''

    return bundle_response(200, "Process started")
    #return(event_body)
    #return( bundle_response(200, {   'message' : get_sample_count(event['queryStringParameters']['location'])}))
