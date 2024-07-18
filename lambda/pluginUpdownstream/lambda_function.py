import os
import re
import shlex
import subprocess

from lambda_utils import download_vcf, Orchestrator, s3


# Environment variables
REFERENCE_GENOME = os.environ['REFERENCE_GENOME']
SVEP_REGIONS = os.environ['SVEP_REGIONS']
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'

BUCKET_NAME = 'svep'
TRANSCRIPT_ID_PATTERN = re.compile('transcript_id\\s\\\"(\\w+)\\\";',
                                   re.IGNORECASE)

# Download reference genome and index
download_vcf(BUCKET_NAME, REFERENCE_GENOME)


def get_stream_direction(pos, metadata):
    strand = metadata[6]
    if strand == '+':
        positive_strand = True
    elif strand == '-':
        positive_strand = False
    else:
        return None
    if pos < min(metadata[3], metadata[4]):
        before = True
    elif pos > max(metadata[3], metadata[4]):
        before = False
    else:
        return None
    return 'up' if positive_strand == before else 'down'


def query_updownstream(chrom, pos, alt, transcripts):
    up = int(pos) - 5000
    down = int(pos) + 5000
    results = []
    loc = f'{chrom}:{up}-{down}'
    local_file = f'/tmp/{REFERENCE_GENOME}'
    args = [
        'tabix',
        local_file,
        loc,
    ]
    query_process = subprocess.Popen(args, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, cwd='/tmp',
                                     encoding='ascii')
    main_data = query_process.stdout.read().rstrip('\n').split('\n')
    for data in main_data:
        if TRANSCRIPT_ID_PATTERN.search(data).group(1) in transcripts:
            continue
        metadata = data.split('\t')
        info = dict(
            strict_split(item)
            for item in metadata[8].split("; ")
        )
        stream_direction = get_stream_direction(pos, metadata)
        transcript_id = info.get('transcript_id', '.').strip('"')
        if stream_direction is None:
            print(f"Couldn't classify - need to check -{transcript_id}")
            results.append('')
            continue
        support_level_set = 'transcript_support_level' in info
        transcript_biotype = info.get('transcript_biotype', '.')
        if not support_level_set:
            transcript_biotype = transcript_biotype.rstrip(';')
        transcript_version = info.get('transcript_version', '.').strip('"')
        fields = [
            '24',
            '.',
            f'{chrom}:{pos}-{pos}',
            alt,
            f'{stream_direction}stream_gene_variant',
            info.get('gene_name', '.').strip('"'),
            info.get('gene_id').strip('"'),
            metadata[2],
            f'{transcript_id}.{transcript_version}',
            transcript_biotype.strip('"'),
            '-',
            '-',
            '-',
            metadata[6],
        ]
        if support_level_set:
            fields.append(
                info.get('transcript_support_level',
                         '.').rstrip(';').strip('"'))
        results.append('\t'.join(fields))
    return '\n'.join(results)


def strict_split(item):
    """Split a string into exactly two strings, or crash."""
    split = shlex.split(item)
    if len(split) != 2:
        raise ValueError(f"Expected two values, got {len(split)} from {item}")
    # Explicit tuple to appease IDE's typechecking
    return split[0], split[1]


def lambda_handler(event, _):
    orchestrator = Orchestrator(event)
    message = orchestrator.message
    sns_data = message['snsData']
    write_data = []

    for row in sns_data:
        chrom = row['chrom']
        pos = row['pos']
        data = row['data']
        alt = row['alt']
        transcripts = []
        results = []
        for dat in data:
            if dat:
                transcripts.append(TRANSCRIPT_ID_PATTERN.search(dat).group(1))
            else:
                write_data.append('\t'.join((
                        str(38),
                        '.',
                        f'{chrom}:{pos}-{pos}',
                        alt,
                        'intergenic_variant',
                        '-',
                        '-',
                        '-',
                        '-',
                        '-',
                        '-',
                        '-',
                        '-',
                        '-',
                        '-',
                )))
                transcripts = []
        if transcripts:
            results = query_updownstream(chrom, pos, alt,
                                         list(set(transcripts)))
        if results:
            write_data.append(results)
    base_filename = orchestrator.temp_file_name
    filename = f'/tmp/{base_filename}.tsv'
    with open(filename, 'w') as tsv_file:
        tsv_file.write('\n'.join(write_data))
    s3.Bucket(SVEP_REGIONS).upload_file(
        filename, f'{base_filename}.tsv')
    print("uploaded")
    orchestrator.mark_completed()
