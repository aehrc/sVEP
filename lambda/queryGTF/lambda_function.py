import datetime
import json
import os
import subprocess
import tempfile
import time
import boto3
import sys

#global vars
PAYLOAD_SIZE = 262000
sns = boto3.client('sns')
s3 = boto3.resource('s3')
MILLISECONDS_BEFORE_SPLIT = 4000
#environ variables
SVEP_TEMP = os.environ['SVEP_TEMP']
REFERENCE_GENOME = os.environ['REFERENCE_GENOME']
PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN = os.environ['PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN']
PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN = os.environ['PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']


def moveReferenceDataToTMP(BUCKET_NAME,keys):
        for KEY in keys:
            local_file_name = '/tmp/'+KEY
            s3.Bucket(BUCKET_NAME).download_file(KEY, local_file_name)

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

def createTempFile(filename):
    print("File created is - ",filename)
    s3.Object(SVEP_TEMP, filename).put(Body=(b""))

def deleteTempFile(APIid,batchID):
    filename = APIid+"_"+batchID
    print("File deleting - ",filename)
    s3.Object(SVEP_TEMP, filename).delete()

def sendDatatoPlugins(topic,results,APIid,uniqueBatchID,tempFileName,lastBatchID):
    kwargs = {}
    createTempFile(tempFileName)
    kwargs["TopicArn"] = topic
    kwargs['Message'] = json.dumps({ "snsData" : results, "APIid":APIid,"batchID":uniqueBatchID,"tempFileName":tempFileName,"lastBatchID":lastBatchID})
    print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
    response = sns.publish(**kwargs)

def sendDatatoItself(remainingCoords, APIid, uniqueBatchID, lastBatchID):
    kwargs = {}
    print("Less Time remaining - call itself.")
    kwargs = {'TopicArn': QUERY_GTF_SNS_TOPIC_ARN,}
    kwargs['Message'] = json.dumps({ "coords" : remainingCoords, "APIid":APIid,"batchID":uniqueBatchID,"lastBatchID":lastBatchID})
    print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
    response = sns.publish(**kwargs)

#testing done
def overlap_feature(all_coords,APIid,batchID,lastBatchID,time_assigned,startTime):
    results = []
    topics = [PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN,PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN]
    num = len(topics)
    finalData = len(all_coords) - 1
    tot_size = 0
    counter = 0
    for idx, coord in enumerate(all_coords):
        test = time.time()

        chr, pos, ref, alt = coord.split('\t')
        loc = chr+":"+pos+"-"+pos
        #changes = all_changes[idx]
        data={}
        localFile = '/tmp/'+REFERENCE_GENOME
        args = ['tabix',localFile,loc]
        query_process = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.PIPE, cwd='/tmp',encoding='ascii')
        mainData = query_process.stdout.read().rstrip('\n').split('\n')
        data = {
            'chrom':chr,
            'pos':pos,
            'ref':ref,
            'alt':alt,
            'data':mainData
        }
        cur_size = get_size(data)
        tot_size += cur_size
        if(tot_size < PAYLOAD_SIZE):
            results.append(data)
            if((time.time() - startTime)*1000 > time_assigned):#should only be executed in very very few cases.
                counter += 1
                uniqueBatchID = batchID +"_"+str(counter)
                print(uniqueBatchID)
                #print("records processed ", idx)
                for topic in topics:
                    tempFileName = APIid+"_"+uniqueBatchID+"_"+topic
                    sendDatatoPlugins(topic,results,APIid,uniqueBatchID,tempFileName,0)

                uniqueBatchID = batchID +"_GTF"+str(counter)
                remainingCoords = all_coords[idx:]
                sendDatatoItself(remainingCoords, APIid, uniqueBatchID, lastBatchID)
                tempFileName = APIid+"_"+uniqueBatchID
                createTempFile(tempFileName)
                deleteTempFile(APIid,batchID)
                break
        else:
            counter += 1
            uniqueBatchID = batchID +"_"+str(counter)
            print(uniqueBatchID)
            #print("records processed ", idx)
            for topic in topics:
                tempFileName = APIid+"_"+uniqueBatchID+"_"+topic
                sendDatatoPlugins(topic,results,APIid,uniqueBatchID,tempFileName,0)
                #print('Received Response: {}'.format(json.dumps(response)))
            #print("Time taken to process %d = %d"%(tot_size,(time.time() - test)*1000))
            #print("Time remaining in lambda = ",context.get_remaining_time_in_millis())
            if((time.time() - startTime)*1000 > time_assigned):
                uniqueBatchID = batchID +"_GTF"+str(counter)
                remainingCoords = all_coords[idx:]
                sendDatatoItself(remainingCoords, APIid, uniqueBatchID, lastBatchID)
                tempFileName = APIid+"_"+uniqueBatchID
                createTempFile(tempFileName)
                deleteTempFile(APIid,batchID)
                break
            else:
                results = []
                tot_size = cur_size
                results.append(data)

        if(idx == finalData):
            counter += 1
            uniqueBatchID = batchID +"_"+str(counter)
            print(uniqueBatchID)
            #createTempFile(APIid,uniqueBatchID)
            #files = counter * num
            for topic in topics:
                tempFileName = APIid+"_"+uniqueBatchID+"_"+topic
                sendDatatoPlugins(topic,results,APIid,uniqueBatchID,tempFileName,lastBatchID)#within lastbatchid - we only want to send the last batch created value of 1..
                #print('Received Response: {}'.format(json.dumps(response)))
            #if(originalBatchID != None):
            #    deleteTempFile(APIid,originalBatchID)
            #else:
            deleteTempFile(APIid,batchID)


def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    time_assigned = (context.get_remaining_time_in_millis()
                     - MILLISECONDS_BEFORE_SPLIT)
    ################test#################
    #message = json.loads(event['Message'])
    #######################################
    message = json.loads(event['Records'][0]['Sns']['Message'])
    coords = message['coords']
    APIid = message['APIid']
    batchID = message['batchID']
    lastBatchID = message['lastBatchID']
    #originalBatchID = None
    #if('originalBatchID' in message):
    #    originalBatchID = message['originalBatchID']

    BUCKET_NAME = 'svep'
    key2 = REFERENCE_GENOME+'.tbi'
    keys = [REFERENCE_GENOME, key2]
    moveReferenceDataToTMP(BUCKET_NAME,keys)
    startTime = time.time()
    overlap_feature(coords,APIid,batchID,lastBatchID,time_assigned,startTime)
    print("This lambda is done. time taken = ", (time.time() - startTime)*1000)
