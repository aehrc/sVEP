import datetime
import json
import os
import subprocess
import time
import boto3
#global vars
s3 = boto3.client('s3')
s3Obj = boto3.resource('s3')
dynamodb = boto3.client('dynamodb')
sns = boto3.client('sns')
#environ variables
SVEP_TEMP = os.environ['SVEP_TEMP']
CONCAT_SNS_TOPIC_ARN = os.environ['CONCAT_SNS_TOPIC_ARN']
SVEP_REGIONS = os.environ['SVEP_REGIONS']
SVEP_RESULTS = os.environ['SVEP_RESULTS']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']



def publishResult( APIid, batchID):
    pre = APIid+"_"+batchID
    if(len(s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=pre)['Contents']) == 2):
        filename = APIid+"_results.tsv"
        bucket = s3Obj.Bucket(SVEP_REGIONS)
        content = []
        for obj in bucket.objects.filter(Prefix=APIid):
            body = obj.get()['Body'].read()
            content.append(body)
        s3Obj.Object(SVEP_RESULTS, filename).put(Body=(b"\n".join(content)))
        print(" Done concatenating")
    else:
        print("last BatchID doesnt exist yet- resending to concat")
        kwargs = {
            'TopicArn': CONCAT_SNS_TOPIC_ARN,
        }
        kwargs['Message'] = json.dumps({'APIid' : APIid,'lastBatchID' : batchID})
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        print('Received Response: {}'.format(json.dumps(response)))

def queryDataset(APIid,batchID):
    objs = s3.list_objects(Bucket=SVEP_TEMP)
    #print(exists(s3.list_objects(Bucket=SVEP_TEMP)['Contents']))
    if('Contents' in objs):
        print("resending for concat")
        kwargs = {
            'TopicArn': CONCAT_SNS_TOPIC_ARN,
        }
        kwargs['Message'] = json.dumps({'APIid' : APIid,'lastBatchID' : batchID})
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        print('Received Response: {}'.format(json.dumps(response)))
    else:
        publishResult(APIid, batchID)


def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    ################test#################
    #message = json.loads(event['Message'])
    #######################################
    message = json.loads(event['Records'][0]['Sns']['Message'])
    APIid = message['APIid']
    batchID = message['lastBatchID']
    #time.sleep(8)
    queryDataset(APIid,batchID)
