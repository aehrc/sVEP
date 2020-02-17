import datetime
import json
import os
import subprocess
import tempfile
import time
import boto3
import sys
import re
import shlex
#global vars
sns = boto3.client('sns')
s3 = boto3.resource('s3')
#environ variables
SVEP_TEMP = os.environ['SVEP_TEMP']
CONCAT_SNS_TOPIC_ARN = os.environ['CONCAT_SNS_TOPIC_ARN']
REFERENCE_GENOME = os.environ['REFERENCE_GENOME']
SVEP_REGIONS = os.environ['SVEP_REGIONS']
os.environ['PATH'] += ':' + os.environ['LAMBDA_TASK_ROOT']



def queryUpdownstream(chrom, pos, alt, transcripts):
        up = int(pos)-5000
        down = int(pos)+5000
        results = []
        loc = str(chrom)+":"+str(up)+"-"+str(down)
        #print(loc)
        #print("position is ", pos)
        args = [
            'tabix',
            REFERENCE_GENOME,loc]
        query_process = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.PIPE, cwd='/tmp',encoding='ascii')
        mainData = query_process.stdout.read().rstrip('\n').split('\n')
        line=""
        for data in mainData:
            #print(data)
            if(re.search('transcript_id\s\\\"(\w+)\\\"\;', data, re.IGNORECASE).group(1) in transcripts):
                continue
            metadata = data.split('\t')
            info = dict(shlex.split(item) for item in metadata[8].split("; "))
            #print(info)
            if(metadata[6] == "+" and pos < metadata[3] and pos < metadata[4]):
                if('transcript_support_level' in info):
                    line= "24"+"\t"+"."+"\t"+chrom+":"+str(pos)+"-"+str(pos)+"\t"+alt+"\t"+"upstream_gene_variant"+"\t"+info["gene_name"].strip('"')+"\t"+info["gene_id"].strip('"')+"\t"+metadata[2]+"\t"+info["transcript_id"].strip('"')+"."+info["transcript_version"].strip('"')+"\t"+info["transcript_biotype"].strip('"')+"\t"+'-'+"\t"+"-"+"\t"+"-"+"\t"+metadata[6]+"\t"+info["transcript_support_level"].rstrip(';').strip('"')
                else:
                    line= "24"+"\t"+"."+"\t"+chrom+":"+str(pos)+"-"+str(pos)+"\t"+alt+"\t"+"upstream_gene_variant"+"\t"+info["gene_name"].strip('"')+"\t"+info["gene_id"].strip('"')+"\t"+metadata[2]+"\t"+info["transcript_id"].strip('"')+"."+info["transcript_version"].strip('"')+"\t"+info["transcript_biotype"].rstrip(';').strip('"')+"\t"+'-'+"\t"+"-"+"\t"+"-"+"\t"+metadata[6]
            elif(metadata[6] == "+" and pos > metadata[3] and pos > metadata[4]):
                if('transcript_support_level' in info):
                    line= "24"+"\t"+"."+"\t"+chrom+":"+str(pos)+"-"+str(pos)+"\t"+alt+"\t"+"downstream_gene_variant"+"\t"+info["gene_name"].strip('"')+"\t"+info["gene_id"].strip('"')+"\t"+metadata[2]+"\t"+info["transcript_id"].strip('"')+"."+info["transcript_version"].strip('"')+"\t"+info["transcript_biotype"].strip('"')+"\t"+'-'+"\t"+"-"+"\t"+"-"+"\t"+metadata[6]+"\t"+info["transcript_support_level"].rstrip(';').strip('"')
                else:
                    line= "24"+"\t"+"."+"\t"+chrom+":"+str(pos)+"-"+str(pos)+"\t"+alt+"\t"+"downstream_gene_variant"+"\t"+info["gene_name"].strip('"')+"\t"+info["gene_id"].strip('"')+"\t"+metadata[2]+"\t"+info["transcript_id"].strip('"')+"."+info["transcript_version"].strip('"')+"\t"+info["transcript_biotype"].rstrip(';').strip('"')+"\t"+'-'+"\t"+"-"+"\t"+"-"+"\t"+metadata[6]
            elif(metadata[6] == "-" and pos < metadata[3] and pos < metadata[4]):
                if('transcript_support_level' in info):
                    line= "24"+"\t"+"."+"\t"+chrom+":"+str(pos)+"-"+str(pos)+"\t"+alt+"\t"+"downstream_gene_variant"+"\t"+info["gene_name"].strip('"')+"\t"+info["gene_id"].strip('"')+"\t"+metadata[2]+"\t"+info["transcript_id"].strip('"')+"."+info["transcript_version"].strip('"')+"\t"+info["transcript_biotype"].strip('"')+"\t"+'-'+"\t"+"-"+"\t"+"-"+"\t"+metadata[6]+"\t"+info["transcript_support_level"].rstrip(';').strip('"')
                else:
                    line= "24"+"\t"+"."+"\t"+chrom+":"+str(pos)+"-"+str(pos)+"\t"+alt+"\t"+"downstream_gene_variant"+"\t"+info["gene_name"].strip('"')+"\t"+info["gene_id"].strip('"')+"\t"+metadata[2]+"\t"+info["transcript_id"].strip('"')+"."+info["transcript_version"].strip('"')+"\t"+info["transcript_biotype"].rstrip(';').strip('"')+"\t"+'-'+"\t"+"-"+"\t"+"-"+"\t"+metadata[6]
            elif(metadata[6] == "-" and pos > metadata[3] and pos > metadata[4]):
                if('transcript_support_level' in info):
                    line= "24"+"\t"+"."+"\t"+chrom+":"+str(pos)+"-"+str(pos)+"\t"+alt+"\t"+"upstream_gene_variant"+"\t"+info["gene_name"].strip('"')+"\t"+info["gene_id"].strip('"')+"\t"+metadata[2]+"\t"+info["transcript_id"].strip('"')+"."+info["transcript_version"].strip('"')+"\t"+info["transcript_biotype"].strip('"')+"\t"+'-'+"\t"+"-"+"\t"+"-"+"\t"+metadata[6]+"\t"+info["transcript_support_level"].rstrip(';').strip('"')
                else:
                    line= "24"+"\t"+"."+"\t"+chrom+":"+str(pos)+"-"+str(pos)+"\t"+alt+"\t"+"upstream_gene_variant"+"\t"+info["gene_name"].strip('"')+"\t"+info["gene_id"].strip('"')+"\t"+metadata[2]+"\t"+info["transcript_id"].strip('"')+"."+info["transcript_version"].strip('"')+"\t"+info["transcript_biotype"].rstrip(';').strip('"')+"\t"+'-'+"\t"+"-"+"\t"+"-"+"\t"+metadata[6]
            else:
                line= "Couldn't classify - need to check -" + info["transcript_id"].strip('"')

            results.append(line)
        #print(results)
        return("\n".join(results))




def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    ################test#################
    #message = json.loads(event['Message'])
    #id = "ksndfkjsndkfnsf"
    #######################################
    message = json.loads(event['Records'][0]['Sns']['Message'])
    snsData = message['snsData']
    APIid = message['APIid']
    batchID = message['batchID']
    tempFileName = message['tempFileName']
    lastBatchID = message['lastBatchID']
    writeData = []
    for row in snsData:
        chrom = row['chrom']
        pos = row['pos']
        data = row['data']
        alt = row['alt']
        transcripts = []
        results = []
        for dat in data:
            if(len(dat) == 0):
                writeData.append(38+"\t"+"."+"\t"+chrom+":"+str(pos)+"-"+str(pos)+"\t"+alt+"\t"+"intergenic_gene_variant")
                transcripts = []
                continue
            transcripts.append(re.search('transcript_id\s\\\"(\w+)\\\"\;', dat, re.IGNORECASE).group(1))
        if(len(transcripts) != 0):
            results = queryUpdownstream(chrom,pos,alt,list(set(transcripts)))
        if (len(results) != 0):
            writeData.append(results)
    filename = "/tmp/"+ APIid+"_upstream.tsv"
    print(batchID)
    with open(filename, 'w') as tsvfile:
        tsvfile.write("\n".join(writeData))
    s3 = boto3.resource('s3')
    s3.Bucket(SVEP_REGIONS).upload_file(filename, APIid+"_"+batchID+"_updownstream.tsv")
    print("uploaded")
    #After processing all the results delete the placeholder temp file from SVEP_TEMP bucket
    s3.Object(SVEP_TEMP, tempFileName).delete()
    print("deleted")
    if(lastBatchID == 1):
        print("sending for concat")
        kwargs = {
            'TopicArn': CONCAT_SNS_TOPIC_ARN,
        }
        kwargs['Message'] = json.dumps({'APIid' : APIid,'lastBatchID' : batchID})
        print('Publishing to SNS: {}'.format(json.dumps(kwargs)))
        response = sns.publish(**kwargs)
        print('Received Response: {}'.format(json.dumps(response)))
