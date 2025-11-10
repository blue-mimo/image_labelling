import json
import boto3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"
s3_client = boto3.client("s3")


def lambda_handler(event, context):
    logger.debug(f"Get labels invoked with event: {json.dumps(event)}")

    if "pathParameters" not in event or "filename" not in event["pathParameters"]:
        logger.error("Filename not provided in path parameters")
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Filename not provided"}),
        }

    filename = event["pathParameters"]["filename"]

    try:
        label_filename = filename.rsplit(".", 1)[0] + ".json"
        logger.info(f"Getting labels for image: {filename} -> {label_filename}")
        logger.debug(f"S3 key: labels/{label_filename}")

        logger.debug("Calling S3 get_object for labels")
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=f"labels/{label_filename}")
        labels = json.loads(obj["Body"].read().decode("utf-8"))
        logger.debug(f"Retrieved labels: {len(labels.get('labels', []))} items")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(labels),
        }
    except Exception as e:
        logger.error(f"Error getting labels for {filename}: {str(e)}")
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }
