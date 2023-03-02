import datetime
import json
import os
import subprocess
import time
import boto3

#global vars
MILLISECONDS_BEFORE_SPLIT = 15000
MILLISECONDS_BEFORE_SECOND_SPLIT = 6000
SLICE_SIZE_MBP = 5
RECORDS_PER_SAMPLE = 700
PAYLOAD_SIZE = 262000
s3 = boto3.resource('s3')
sns = boto3.client('sns')
#environ variables
SVEP_TEMP = os.environ['SVEP_TEMP']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
QUERY_VCF_SUBMIT_SNS_TOPIC_ARN = os.environ['QUERY_VCF_SUBMIT_SNS_TOPIC_ARN']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']


def createTempFile(APIid,batchID):
    filename = APIid+"_"+batchID
    s3.Object(SVEP_TEMP, filename).put(Body=(b""))

def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    time_assigned = (context.get_remaining_time_in_millis()-MILLISECONDS_BEFORE_SPLIT)
    #print("time assigned",time_assigned)
    timeStart = time.time()
    message = json.loads(event['Records'][0]['Sns']['Message'])
    total_coords = message['coords']
    requestID = message['requestID']
    batchID = message['batchID']
    lastBatchID = message['lastBatchID']
    print(total_coords)
    print(batchID)
    kwargs = {
        'TopicArn': QUERY_GTF_SNS_TOPIC_ARN,
    }
    print("length = ",len(total_coords) )
    finalData = len(total_coords) - 1
    for idx in range(len(total_coords)):

        if((idx == finalData) and (lastBatchID == 1) ):
            newBatchID = batchID+"_"+str(idx)
            print(newBatchID)
            createTempFile(requestID,newBatchID)
            kwargs['Message'] = json.dumps({
                'coords':total_coords[idx],
                #'changes':total_changes[idx],
                'APIid':requestID,
                'batchID':newBatchID,
                'lastBatchID' : lastBatchID
            })
        else:
            newBatchID = batchID+"_"+str(idx)
            print(newBatchID)
            createTempFile(requestID,newBatchID)
            kwargs['Message'] = json.dumps({
                'coords':total_coords[idx],
                #'changes':total_changes[idx],
                'APIid':requestID,
                'batchID':newBatchID,
                'lastBatchID': 0
            })
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        #print('Received Response: {}'.format(json.dumps(response)))
        #return(batchID)
