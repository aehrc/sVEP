import datetime
import json
import os
import subprocess
import time
import boto3
import sys
from api_response import bad_request, bundle_response, missing_parameter
from chrom_matching import CHROMOSOME_LENGTHS_MBP, get_vcf_chromosomes, get_matching_chromosome
#global vars
MILLISECONDS_BEFORE_SPLIT = 15000
MILLISECONDS_BEFORE_SECOND_SPLIT = 8000
SLICE_SIZE_MBP = 5
RECORDS_PER_SAMPLE = 700
BATCH_CHUNK_SIZE = 10
PAYLOAD_SIZE = 262000
s3 = boto3.resource('s3')
sns = boto3.client('sns')
#environ variables
SVEP_TEMP = os.environ['SVEP_TEMP']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
QUERY_VCF_EXTENDED_SNS_TOPIC_ARN = os.environ['QUERY_VCF_EXTENDED_SNS_TOPIC_ARN']
QUERY_VCF_SUBMIT_SNS_TOPIC_ARN = os.environ['QUERY_VCF_SUBMIT_SNS_TOPIC_ARN']
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
    print("get regions time = ",(time.time() - test)*1000)
    return query_process

def get_regions_and_variants(location, chrom, start, end, time_assigned):
    regions_process = get_regions(location,chrom, start, end)
    return regions_process

def createTempFile(APIid,batchID):
    filename = APIid+"_"+batchID
    s3.Object(SVEP_TEMP, filename).put(Body=(b""))

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

def submitQueryGTF(regions_process, requestID, regionID,lastBatchID,time_assigned_second_split,timeStart):
    kwargs = {
        'TopicArn': QUERY_GTF_SNS_TOPIC_ARN,
    }

    test = time.time()
    regions_list = regions_process.stdout.read().splitlines()
    print("read  time = ",(time.time() - test)*1000)
    total_coords = [regions_list[x:x+RECORDS_PER_SAMPLE] for x in range(0, len(regions_list), RECORDS_PER_SAMPLE)]
    print("read and split data time = ",(time.time() - test)*1000)
    print(total_coords)

    print("length = ",len(total_coords) )
    finalData = len(total_coords) - 1
    for idx in range(len(total_coords)):
        if((time.time() - timeStart)*1000 > time_assigned_second_split):
            remainingCoords = total_coords[idx:]
            batchID = regionID+"_"+str(idx)
            print("remaining Coords length ",len(remainingCoords))
            print("remaining Coords  ",(remainingCoords))
            tot_size = get_size(remainingCoords)
            kwargs = {'TopicArn': QUERY_VCF_SUBMIT_SNS_TOPIC_ARN,}
            if(tot_size < PAYLOAD_SIZE): #remaining coords could still be too big for SNS to handle
                #call itself with remaining data
                kwargs['Message'] = json.dumps({'coords' : remainingCoords,'requestID' : requestID, 'batchID': batchID,'lastBatchID': lastBatchID})
                print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
                response = sns.publish(**kwargs)
                print('Received Response: {}'.format(json.dumps(response)))
                break
            else: # Since coords are generally similar size because its made of chr, loc, ref, alt - we know 10batches of 700 records can be handled by SNS
                for i in range(0, len(remainingCoords), BATCH_CHUNK_SIZE):
                    newRemainingCoords = remainingCoords[i:i+BATCH_CHUNK_SIZE]
                    newBatchID = batchID+"_sns"+str(i)
                    kwargs['Message'] = json.dumps({'coords' : newRemainingCoords,'requestID' : requestID, 'batchID': newBatchID,'lastBatchID': lastBatchID})
                    print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
                    response = sns.publish(**kwargs)
                    print('Received Response: {}'.format(json.dumps(response)))
                break

        else:
            if((idx == finalData) and (lastBatchID == 1) ):
                batchID = regionID+"_"+str(idx)
                print(batchID)
                createTempFile(requestID,batchID)
                kwargs['Message'] = json.dumps({
                    'coords':total_coords[idx],
                    #'changes':total_changes[idx],
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
                    #'changes':total_changes[idx],
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
    time_assigned_second_split = (context.get_remaining_time_in_millis()-MILLISECONDS_BEFORE_SECOND_SPLIT)
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
            regions_process = get_regions_and_variants(location, chrom, start, end, time_assigned)
            #total_coords = [all_coords[x:x+RECORDS_PER_SAMPLE] for x in range(0, len(all_coords), RECORDS_PER_SAMPLE)]
            #total_changes = [all_changes[x:x+RECORDS_PER_SAMPLE] for x in range(0, len(all_changes), RECORDS_PER_SAMPLE)]
            if (index == finalData):
                submitQueryGTF(regions_process,requestID,regionID,1,time_assigned_second_split,timeStart)
            else:
                submitQueryGTF(regions_process,requestID,regionID,0,time_assigned_second_split,timeStart)



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
