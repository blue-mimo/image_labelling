import json
import boto3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"
s3_client = boto3.client("s3")


def lambda_handler(event, context):
    logger.debug(f"List images invoked with event: {json.dumps(event)}")
    logger.info(f"Listing images from bucket: {BUCKET_NAME}")

    try:
        logger.debug("Calling S3 list_objects_v2")
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="uploads/")
        keys = [obj["Key"] for obj in response.get("Contents", []) if "Key" in obj]
        images = [
            key.replace("uploads/", "")
            for key in keys
            if key != "uploads/" and key.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        logger.debug(f"Found {len(keys)} total objects, {len(images)} image files")
        logger.info(f"Returning {len(images)} images: {images}")
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(images),
        }
    except Exception as e:
        logger.error(f"Error listing images: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }
