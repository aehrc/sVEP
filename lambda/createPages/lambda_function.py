import datetime
import json
import os
import subprocess
import time
import sys
import boto3

#global vars
s3 = boto3.client('s3')
s3Obj = boto3.resource('s3')
sns = boto3.client('sns')
allFiles =[]
#environ variables
SVEP_REGIONS = os.environ['SVEP_REGIONS']
SVEP_RESULTS = os.environ['SVEP_RESULTS']
CONCATPAGES_SNS_TOPIC_ARN = os.environ['CONCATPAGES_SNS_TOPIC_ARN']
CREATEPAGES_SNS_TOPIC_ARN = os.environ['CREATEPAGES_SNS_TOPIC_ARN']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']

def publishResult(APIid,pageKeys, pageNum,prefix,dontAppend, lastPage):
    filename = prefix+str(pageNum)+"concatenated.tsv"
    allFiles.append(filename)
    content=[]
    if(dontAppend == 0):
        for pageKey in pageKeys:
        #    print(pageContent['Key'])
            obj = s3.get_object(Bucket=SVEP_REGIONS, Key=pageKey)
            body = obj['Body'].read()
            #body = body +b"\n"
            content.append(body)
            #s3Obj.Object(Bucket=SVEP_REGIONS, Key=pageKey).delete()
        #todo - cleanup - delete the obj once the content is read and stored in memory
        s3Obj.Object(SVEP_REGIONS, filename).put(Body=(b"\n".join(content)))#add \n if necessary
    #print(" Done concatenating")
    if(lastPage == 1):
        print(prefix)
        bucketLen = len(s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=prefix)['Contents'])
        if( bucketLen != pageNum):
            print("calling itself again to make sure all files are done.")
            kwargs = {'TopicArn': CREATEPAGES_SNS_TOPIC_ARN,}
            kwargs['Message'] = json.dumps({'APIid':APIid,'pageKeys' : pageKeys,'pageNum' : pageNum,'prefix' :prefix,'dontAppend' : 1,'lastPage': 1})
            print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
            response = sns.publish(**kwargs)
            #print('Received Response: {}'.format(json.dumps(response)))
        elif( bucketLen == pageNum and bucketLen > 10):
            newPrefix = prefix+'_round'
            kwargs = {'TopicArn': CREATEPAGES_SNS_TOPIC_ARN,}
            prefixFiles = s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=prefix)['Contents']
            prefixKeys = [d['Key'] for d in prefixFiles]

            allKeys = [prefixKeys[x:x+20] for x in range(0, len(prefixKeys), 20)]
            print("length of all keys =", len(allKeys))
            totalLen = len(allKeys)
            for idx,key in enumerate(allKeys, start=1):
                if(idx == totalLen):
                    kwargs['Message'] = json.dumps({'APIid':APIid,'pageKeys' : allKeys[idx-1],'pageNum' : idx,'prefix' :newPrefix,'lastPage': 1})
                    print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
                    response = sns.publish(**kwargs)
                    #print('Received Response: {}'.format(json.dumps(response)))
                else:
                    kwargs['Message'] = json.dumps({'APIid':APIid,'pageKeys' : allKeys[idx-1],'pageNum' : idx,'prefix' :newPrefix,'lastPage': 0})
                    print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
                    response = sns.publish(**kwargs)
                    #print('Received Response: {}'.format(json.dumps(response)))

        elif( bucketLen == pageNum and bucketLen < 10):
                #if(lastPage == 1 && len(allFiles) == 1):
                print("last page and all combined")
                Files = s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=prefix)['Contents']
                allKeys = [d['Key'] for d in Files]

                kwargs = {
                    'TopicArn': CONCATPAGES_SNS_TOPIC_ARN,
                }
                kwargs['Message'] = json.dumps({'APIid' : APIid,'allKeys':allKeys,'lastFile' : filename,'pageNum' : pageNum, 'prefix': prefix})
                print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
                response = sns.publish(**kwargs)
                #print('Received Response: {}'.format(json.dumps(response)))
                    #trigger another lambda to concat all pages
        elif(bucketLen == 1):
            resultFile = APIid+"_results.tsv"
            prefixFiles = s3.list_objects_v2(Bucket=SVEP_REGIONS, Prefix=prefix)['Contents']
            prefixKeys = prefixFiles[0]['Key']
            copy_source = {
                'Bucket': SVEP_REGIONS,
                'Key': prefixKeys
            }
            s3.meta.client.copy(copy_source, SVEP_RESULTS , resultFile)


def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    ################test#################
    #message = json.loads(event['Message'])
    #######################################
    message = json.loads(event['Records'][0]['Sns']['Message'])
    APIid = message['APIid']
    pageKeys = message['pageKeys']
    pageNum = message['pageNum']
    prefix = message['prefix']
    lastPage = message['lastPage']
    dontAppend = 0
    if('dontAppend' in message):
        dontAppend = message['dontAppend']
    #time.sleep(8)
    publishResult(APIid,pageKeys, pageNum,prefix,dontAppend, lastPage)
