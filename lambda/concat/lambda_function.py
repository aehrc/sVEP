import datetime
import json
import os
import subprocess
import time
import boto3

CONCAT_SNS_TOPIC_ARN = os.environ['CONCAT_SNS_TOPIC_ARN']
DATASETS_TABLE_NAME = os.environ['DATASETS_TABLE']
SVEP_REGIONS = os.environ['SVEP_REGIONS']
SVEP_RESULTS = os.environ['SVEP_RESULTS']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']
s3 = boto3.client('s3')
s3Obj = boto3.resource('s3')
dynamodb = boto3.client('dynamodb')
sns = boto3.client('sns')


def publishResult(numFiles, APIid, batchID):
    filename = APIid+"_results.tsv"
    bucket = s3Obj.Bucket(SVEP_REGIONS)
    files =[]
    content = []
    for key in s3.list_objects(Bucket=SVEP_REGIONS)['Contents']:
        if(key['Key'].startswith(APIid)):
            files.append(key['Key'])
    if(numFiles == len(files)):
        for obj in bucket.objects.filter(Prefix=APIid):
            body = obj.get()['Body'].read()
            content.append(body)

        s3Obj.Object(SVEP_RESULTS, filename).put(Body=(b"\n".join(content)))
        #with open("/tmp/merge.tsv", 'w') as tsvfile:
        #    tsvfile.write("\n".join(content))

        #s3Obj.Bucket(SVEP_RESULTS).upload_file("/tmp/merge.tsv", filename)
    else:
        print("resending for concat")
        kwargs = {
            'TopicArn': CONCAT_SNS_TOPIC_ARN,
        }
        kwargs['Message'] = json.dumps({'APIid' : APIid,'lastBatchID' : batchID})
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        print('Received Response: {}'.format(json.dumps(response)))


def queryDataset(APIid,batchID):
    kwargs = {
        'TableName': DATASETS_TABLE_NAME,
        'Key': {
            'APIid': {
                'S': APIid,
            },
        },
    }
    response = dynamodb.get_item(**kwargs)
    numFiles = int(response['Item']['filesCount']['N'])
    publishResult(numFiles, APIid, batchID)



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
