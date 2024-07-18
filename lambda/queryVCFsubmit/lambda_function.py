import os


from lambda_utils import Orchestrator, start_function


# Environment variables
QUERY_GTF_SNS_TOPIC_ARN = os.environ['QUERY_GTF_SNS_TOPIC_ARN']


def lambda_handler(event, _):
    orchestrator = Orchestrator(event)
    message = orchestrator.message
    total_coords = message['coords']
    print(f"length = {len(total_coords)}")
    base_filename = orchestrator.temp_file_name
    for idx in range(len(total_coords)):
        start_function(
            topic_arn=QUERY_GTF_SNS_TOPIC_ARN,
            base_filename=f'{base_filename}_{idx}',
            message={
                'coords': total_coords[idx],
            },
        )
    orchestrator.mark_completed()
