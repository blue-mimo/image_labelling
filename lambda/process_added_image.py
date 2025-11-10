"""
Lambda function for automatic image labeling using Amazon Rekognition.
This function is triggered when an image is uploaded to the S3 bucket.
"""

import json
import boto3
import logging
from urllib.parse import unquote_plus
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Initialize AWS clients (will be set on first use or can be mocked for testing)
s3_client = None
rekognition_client = None
dynamodb = None


def get_s3_client():
    """Get or create S3 client."""
    global s3_client
    if s3_client is None:
        s3_client = boto3.client("s3")
    return s3_client


def get_rekognition_client():
    """Get or create Rekognition client."""
    global rekognition_client
    if rekognition_client is None:
        rekognition_client = boto3.client("rekognition")
    return rekognition_client


def get_dynamodb_resource():
    """Get or create DynamoDB resource."""
    global dynamodb
    if dynamodb is None:
        dynamodb = boto3.resource("dynamodb")
    return dynamodb


def lambda_handler(event, context):
    """
    Lambda function to label images using Amazon Rekognition.
    Triggered when an image is uploaded to the S3 bucket.

    Args:
        event: S3 event containing bucket and object information
        context: Lambda context object

    Returns:
        dict: Response with status code and message
    """
    logger.debug(f"Lambda invoked with event: {json.dumps(event)}")
    logger.debug(f"Context: {context}")

    try:
        # Get clients
        s3 = get_s3_client()
        rekognition = get_rekognition_client()
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table("image_labels")
        logger.debug("AWS clients initialized")

        # Parse the S3 event
        logger.debug(f"Processing {len(event['Records'])} records")
        for record in event["Records"]:
            bucket = record["s3"]["bucket"]["name"]
            key = unquote_plus(record["s3"]["object"]["key"])

            if not key.lower().endswith((".jpg", ".jpeg", ".png")):
                logger.info(f"Skipping non-image file: {key}")
                continue

            logger.info(f"Processing image: {key} from bucket: {bucket}")
            logger.debug(
                f'Image size: {record["s3"]["object"].get("size", "unknown")} bytes'
            )

            # Call Amazon Rekognition to detect labels
            logger.debug("Calling Rekognition detect_labels")
            response = rekognition.detect_labels(
                Image={"S3Object": {"Bucket": bucket, "Name": key}},
                MaxLabels=10,
                MinConfidence=75,
            )

            # Save the labels to DynamoDB
            image_name = key.replace("uploads/", "")

            logger.info(f"Detected {len(response['Labels'])} labels")

            # Store individual label records with composite key
            for label in response["Labels"]:
                table.put_item(
                    Item={
                        "image_name": image_name,
                        "label_name": label["Name"].lower(),
                        "confidence": Decimal(str(label["Confidence"])),
                    }
                )

            logger.info(f"Labels saved to DynamoDB for image: {image_name}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Image labeling completed successfully",
                    "processed_images": len(event["Records"]),
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise
