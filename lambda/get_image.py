import base64
import boto3
import json
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"
s3_client = boto3.client("s3")

_CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
}


def lambda_handler(event, context):
    logger.debug(f"Get image invoked with event: {json.dumps(event)}")

    if "pathParameters" not in event or "filename" not in event["pathParameters"]:
        logger.error("Filename not provided in path parameters")
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": '{"error": "Filename not provided"}',
        }

    image_filename = event["pathParameters"]["filename"]

    try:
        logger.info(f"Getting image: {image_filename}")
        logger.debug(f"S3 key: uploads/{image_filename}")

        logger.debug("Calling S3 get_object for image")
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=f"uploads/{image_filename}")
        image_data = obj["Body"].read()
        logger.debug(f"Retrieved image data: {len(image_data)} bytes")

        extension = image_filename[image_filename.rfind(".") :].lower()
        content_type = _CONTENT_TYPE_MAP.get(extension, "application/octet-stream")
        logger.debug(f"Content type for {extension}: {content_type}")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": content_type,
                "Access-Control-Allow-Origin": "*",
            },
            "body": base64.b64encode(image_data).decode("utf-8"),
            "isBase64Encoded": True,
        }
    except Exception as e:
        logger.error(f"Error getting image {image_filename}: {str(e)}")
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": f'{{"error": "{str(e)}"}}',
        }
