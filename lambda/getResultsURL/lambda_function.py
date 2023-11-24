import os

from api_response import bad_request, bundle_response
from lambda_utils import (
    print_event,
    generate_presigned_get_url,
)


# Environment variables
RESULT_BUCKET = os.environ["SVEP_RESULTS"]
RESULT_DURATION = int(os.environ["RESULT_DURATION"])
RESULT_SUFFIX = os.environ["RESULT_SUFFIX"]


def lambda_handler(event, _):
    print_event(event, max_length=None)
    try:
        request_id = event["queryStringParameters"]["request_id"]
        result_url = generate_presigned_get_url(
            RESULT_BUCKET, f"{request_id}{RESULT_SUFFIX}", RESULT_DURATION
        )
    except ValueError:
        return bad_request("Error parsing request body, Expected JSON.")

    return bundle_response(
        200,
        {
            "ResultUrl": result_url,
        },
    )
