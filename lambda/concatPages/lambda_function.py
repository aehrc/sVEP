import datetime
import json
import os
import subprocess
import time
import sys
import boto3
import s3fs
#global vars
fs = s3fs.S3FileSystem(anon=False)
s3 = boto3.client('s3')
s3Obj = boto3.resource('s3')
sns = boto3.client('sns')
#environ variables
SVEP_REGIONS = os.environ['SVEP_REGIONS']
SVEP_RESULTS = os.environ['SVEP_RESULTS']
CONCATPAGES_SNS_TOPIC_ARN = os.environ['CONCATPAGES_SNS_TOPIC_ARN']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']


def publishResult(APIid, allKeys, lastFile, pageNum,prefix,context):
    startTime = time.time()
    #pre = APIid+"_page"
    filename = APIid+"_results.tsv"
    filePath = "s3://"+SVEP_RESULTS+"/"+filename
    #if(len(s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=lastFile)['Contents']) == 1):
    if(len(s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=prefix)['Contents']) == pageNum):
        Files = s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=prefix)['Contents']
        #allKeys = [d['Key'] for d in Files]
        paths = [SVEP_REGIONS+"/"+d for d in allKeys]
        #paths = [SVEP_REGIONS+"/"+d['Key'] for d in Files]
        fs.merge(path=filePath,filelist=paths)
        content = []
        print("time taken = ", (time.time() - startTime)*1000)
        print(" Done concatenating")
    else:
        print("createPages failed to create one of the page")
        kwargs = {
            'TopicArn': CONCATPAGES_SNS_TOPIC_ARN,
        }
        kwargs['Message'] = json.dumps({'APIid' : APIid,'lastFile' : lastFile,'pageNum' : pageNum})
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        #print('Received Response: {}'.format(json.dumps(response)))
    '''else:
        print("Still waiting for the last page to be created")
        kwargs = {
            'TopicArn': CONCATPAGES_SNS_TOPIC_ARN,
        }
        kwargs['Message'] = json.dumps({'APIid' : APIid,'lastFile' : lastFile,'pageNum' : pageNum})
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        #print('Received Response: {}'.format(json.dumps(response)))'''


def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    ################test#################
    #message = json.loads(event['Message'])
    #######################################
    message = json.loads(event['Records'][0]['Sns']['Message'])
    APIid = message['APIid']
    allKeys = message['allKeys']
    lastFile = message['lastFile']
    pageNum = message['pageNum']
    prefix = message['prefix']

    #time.sleep(8)
    publishResult(APIid,allKeys,lastFile, pageNum,prefix,context)
