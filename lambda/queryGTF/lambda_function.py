import datetime
import json
import os
import subprocess
import tempfile
import time
import boto3
import sys

PAYLOAD_SIZE = 262000
DATASETS_TABLE_NAME = os.environ['DATASETS_TABLE']
REFERENCE_GENOME = os.environ['REFERENCE_GENOME']
PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN = os.environ['PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN']
PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN = os.environ['PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']
sns = boto3.client('sns')
dynamodb = boto3.client('dynamodb')
s3 = boto3.resource('s3')

#testing done
def overlap_feature(all_coords,all_changes):
    results = []
    BUCKET_NAME = 'svep'
    keys = ['sorted_filtered_Homo_sapiens.GRCh38.98.chr.gtf.gz', 'sorted_filtered_Homo_sapiens.GRCh38.98.chr.gtf.gz.tbi']
    for KEY in keys:
        local_file_name = '/tmp/'+KEY
        s3.Bucket(BUCKET_NAME).download_file(KEY, local_file_name)

    for idx, coord in enumerate(all_coords):
        chr, pos = coord.split('\t')
        loc = chr+":"+pos+"-"+pos
        changes = all_changes[idx]
        data={}
        args = ['tabix','/tmp/sorted_filtered_Homo_sapiens.GRCh38.98.chr.gtf.gz',loc]
        query_process = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.PIPE, cwd='/tmp',encoding='ascii')
        mainData = query_process.stdout.read().rstrip('\n').split('\n')
        data = {
            'chrom':chr,
            'pos':pos,
            'ref':changes.split('\t')[0],
            'alt':changes.split('\t')[1],
            'data':mainData
        }
        results.append(data)

    return results

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

def updateDataset(APIid,batchID,counter):
    kwargs = {
        'TableName': DATASETS_TABLE_NAME,
        'Key': {
            'APIid': {
                'S': APIid,
            },
        },
        'UpdateExpression': 'ADD filesCount :c ',
        'ExpressionAttributeValues': { ':c' :{'N':str(counter)} },
    }
    print('Updating Count of files: {}'.format(json.dumps(kwargs)))
    dynamodb.update_item(**kwargs)
    kwargs = {
        'TableName': DATASETS_TABLE_NAME,
        'Key': {
            'APIid': {
                'S': APIid,
            },
        },
        'UpdateExpression': 'DELETE batchID :b ',
        'ExpressionAttributeValues': { ':b' :{'SS':[batchID]} },
    }
    print('Deleting batch id item: {}'.format(json.dumps(kwargs)))
    dynamodb.update_item(**kwargs)

def publish_consequences_plugin(slice_data,APIid,batchID,lastBatchID):
    topics = [PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN,PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN]
    num = len(topics)
    kwargs = {}
    finalData = len(slice_data) - 1
    snsData = []
    tot_size = 0
    counter = 0
    for idx, slice_datum in enumerate(slice_data):
        print(json.dumps(slice_datum))
        cur_size = get_size(slice_datum)
        tot_size += cur_size
        if(tot_size < PAYLOAD_SIZE):
            snsData.append(slice_datum)
        else:
            counter += 1
            uniqueBatchID = batchID +"_"+str(counter)
            print(uniqueBatchID)
            for topic in topics:
                #"TopicArn": PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN,
                kwargs["TopicArn"] = topic
                kwargs['Message'] = json.dumps({ "snsData" : snsData, "APIid":APIid,"batchID":uniqueBatchID,"lastBatchID":0})
                print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
                response = sns.publish(**kwargs)
                print('Received Response: {}'.format(json.dumps(response)))
            snsData = []
            tot_size = cur_size
            snsData.append(slice_datum)

        if(idx == finalData):
            counter += 1
            uniqueBatchID = batchID +"_"+str(counter)
            print(uniqueBatchID)
            files = counter * num
            for topic in topics:
                kwargs["TopicArn"] = topic
                kwargs['Message'] = json.dumps({ "snsData" : snsData, "APIid":APIid,"batchID":uniqueBatchID,"lastBatchID":lastBatchID})
                print('Publishing to SNS: {}'.format(kwargs))
                response = sns.publish(**kwargs)
                print('Received Response: {}'.format(json.dumps(response)))
            updateDataset(APIid,batchID,files)





def annotate_slice(all_coords, all_changes,APIid,batchID,lastBatchID):
        overlap_list = overlap_feature(all_coords,all_changes)
        publish_consequences_plugin(overlap_list,APIid,batchID,lastBatchID)

def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    ################test#################
    #message = json.loads(event['Message'])
    #######################################
    message = json.loads(event['Records'][0]['Sns']['Message'])
    coords = message['coords']
    changes = message['changes']
    APIid = message['APIid']
    batchID = message['batchID']
    lastBatchID = message['lastBatchID']
    annotate_slice(coords,changes,APIid,batchID,lastBatchID)
