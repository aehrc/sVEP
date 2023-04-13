import os


from lambda_utils import create_temp_file, get_sns_event, sns_publish


# Environment variables
SVEP_TEMP = os.environ['SVEP_TEMP']
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']
os.environ['PATH'] += f':{os.environ["LAMBDA_TASK_ROOT"]}'


def lambda_handler(event, _):
    message = get_sns_event(event)
    total_coords = message['coords']
    request_id = message['requestID']
    batch_id = message['batchID']
    last_batch = message['lastBatch']
    print(total_coords)
    print(batch_id)
    print(f"length = {len(total_coords)}")
    final_data = len(total_coords) - 1
    for idx in range(len(total_coords)):
        is_last = (idx == final_data) and last_batch
        new_batch_id = f'{batch_id}_{str(idx)}'
        print(new_batch_id)
        create_temp_file(SVEP_TEMP, request_id, new_batch_id)
        sns_publish(QUERY_GTF_SNS_TOPIC_ARN, {
            'coords': total_coords[idx],
            'APIid': request_id,
            'batchID': new_batch_id,
            'lastBatch': is_last,
        })
