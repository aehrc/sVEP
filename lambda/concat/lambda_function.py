import datetime
import json
import os
import subprocess
import time
import sys
import boto3
from smart_open_reduced import BufferedOutputBase
#global vars
s3 = boto3.client('s3')
s3Obj = boto3.resource('s3')
sns = boto3.client('sns')
#environ variables
SVEP_TEMP = os.environ['SVEP_TEMP']
CONCAT_SNS_TOPIC_ARN = os.environ['CONCAT_SNS_TOPIC_ARN']
CREATEPAGES_SNS_TOPIC_ARN = os.environ['CREATEPAGES_SNS_TOPIC_ARN']
SVEP_REGIONS = os.environ['SVEP_REGIONS']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']



def publishResult( APIid, batchID):
    pre = APIid+"_"+batchID

    if(len(s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=pre)['Contents']) == 2):
        bucket = s3Obj.Bucket(SVEP_REGIONS)
        content = []
        pageNum =0
        paginator = s3.get_paginator('list_objects_v2')
        operation_parameters = {'Bucket': SVEP_REGIONS,
                                'Prefix': APIid,
                                'PaginationConfig' : {  'PageSize': 600}} #change later on
        page_iterator = paginator.paginate(**operation_parameters)
        kwargs = {
            'TopicArn': CREATEPAGES_SNS_TOPIC_ARN,
        }

        for page in page_iterator:
        #for obj in bucket.objects.filter(Prefix=APIid):
            pageContents = page['Contents']
            pageKeys = [d['Key'] for d in pageContents]
            pageNum+=1
            prefix=APIid+"_page"
            if('NextContinuationToken' in page):
                kwargs['Message'] = json.dumps({'APIid':APIid,'pageKeys' : pageKeys,'pageNum' : pageNum,'prefix' :prefix,'lastPage': 0})
                print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
                response = sns.publish(**kwargs)
                #print('Received Response: {}'.format(json.dumps(response)))
            else:
                print("last page")
                print(pageNum)
                kwargs['Message'] = json.dumps({'APIid':APIid,'pageKeys' : pageKeys,'pageNum' : pageNum,'prefix' :prefix,'lastPage': 1})
                print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
                response = sns.publish(**kwargs)

                #print('Received Response: {}'.format(json.dumps(response)))
        print(" Done sending to CREATEPAGES")
    else:
        print("last BatchID doesnt exist yet- resending to concat")
        kwargs = {
            'TopicArn': CONCAT_SNS_TOPIC_ARN,
        }
        kwargs['Message'] = json.dumps({'APIid' : APIid,'lastBatchID' : batchID})
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        #print('Received Response: {}'.format(json.dumps(response)))

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
        #print('Received Response: {}'.format(json.dumps(response)))
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
