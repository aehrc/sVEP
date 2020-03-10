import datetime
import json
import os
import subprocess
import time
import sys
import boto3
#from smart_open_reduced import BufferedOutputBase
#global vars
s3 = boto3.client('s3')
s3Obj = boto3.resource('s3')
dynamodb = boto3.client('dynamodb')
sns = boto3.client('sns')
#environ variables
SVEP_REGIONS = os.environ['SVEP_REGIONS']
CONCATPAGES_SNS_TOPIC_ARN = os.environ['CONCATPAGES_SNS_TOPIC_ARN']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']

def publishResult(APIid,pageKeys, pageNum, lastPage):
    filename = APIid+"_page"+str(pageNum)+"concatenated.tsv"
    content=[]
    for pageKey in pageKeys:
    #    print(pageContent['Key'])
        obj = s3.get_object(Bucket=SVEP_REGIONS, Key=pageKey)
        body = obj['Body'].read()
        content.append(body)
        #todo - cleanup - delete the obj once the content is read and stored in memory
    s3Obj.Object(SVEP_REGIONS, filename).put(Body=(b"".join(content)))#add \n if necessary
    print(" Done concatenating")
    if(lastPage == 1):
        print("last page")
        kwargs = {
            'TopicArn': CONCATPAGES_SNS_TOPIC_ARN,
        }
        kwargs['Message'] = json.dumps({'APIid' : APIid,'lastFile' : filename,'pageNum' : pageNum})
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        print('Received Response: {}'.format(json.dumps(response)))
        #trigger another lambda to concat all pages

def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    ################test#################
    #message = json.loads(event['Message'])
    #######################################
    message = json.loads(event['Records'][0]['Sns']['Message'])
    APIid = message['APIid']
    pageKeys = message['pageKeys']
    pageNum = message['pageNum']
    lastPage = message['lastPage']
    #time.sleep(8)
    publishResult(APIid,pageKeys, pageNum, lastPage)
