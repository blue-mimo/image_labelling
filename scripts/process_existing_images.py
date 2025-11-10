#!/usr/bin/env python3
"""
Script to process all existing images in S3 bucket and create DynamoDB label entries.
This script iterates through all images in the uploads/ folder and generates labels using Rekognition.
"""

import boto3
import logging
from decimal import Decimal
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"


def process_existing_images():
    """Process all existing images in S3 bucket"""

    # Initialize AWS clients
    s3_client = boto3.client("s3")
    rekognition_client = boto3.client("rekognition")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("image_labels")

    logger.info("Starting processing of existing images...")

    try:
        # Get all images from S3
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="uploads/")
        objects = response.get("Contents", [])

        # Handle pagination
        while response.get("IsTruncated", False):
            response = s3_client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix="uploads/",
                ContinuationToken=response["NextContinuationToken"],
            )
            objects.extend(response.get("Contents", []))

        # Filter for image files
        image_keys = [
            key
            for key in [obj.get("Key", "") for obj in objects]
            if key != "uploads/" and key.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        logger.info(f"Found {len(image_keys)} images to process")

        processed_count = 0
        error_count = 0

        for key in image_keys:
            image_name = key.replace("uploads/", "")

            try:
                logger.info(f"Processing image: {image_name}")

                # Call Amazon Rekognition to detect labels
                response = rekognition_client.detect_labels(
                    Image={"S3Object": {"Bucket": BUCKET_NAME, "Name": key}},
                    MaxLabels=10,
                    MinConfidence=75,
                )

                labels = response.get("Labels", [])
                logger.info(f"Detected {len(labels)} labels for {image_name}")

                # Get existing labels from DynamoDB
                existing_response = table.query(
                    KeyConditionExpression="image_name = :img",
                    ExpressionAttributeValues={":img": image_name},
                )
                existing_labels = {
                    item["label_name"] for item in existing_response["Items"]
                }

                # Get new labels from Rekognition (deduplicate by taking highest confidence)
                new_labels = {}
                for label in labels:
                    label_name = label["Name"].lower()
                    if (
                        label_name not in new_labels
                        or label["Confidence"] > new_labels[label_name]
                    ):
                        new_labels[label_name] = label["Confidence"]

                # Delete labels not in Rekognition response
                labels_to_delete = existing_labels - set(new_labels.keys())
                for label_name in labels_to_delete:
                    table.delete_item(
                        Key={"image_name": image_name, "label_name": label_name}
                    )

                # Add new labels
                labels_to_add = set(new_labels.keys()) - existing_labels
                for label_name in labels_to_add:
                    logger.debug(
                        f"Adding item  {image_name}#{label_name}: {new_labels[label_name]:.1f}"
                    )
                    table.put_item(
                        Item={
                            "image_name": image_name,
                            "label_name": label_name,
                            "confidence": Decimal(str(new_labels[label_name])),
                        }
                    )

                logger.info(
                    f"Deleted {len(labels_to_delete)}, added {len(labels_to_add)} labels"
                )

                processed_count += 1
                logger.debug(f"Successfully processed {image_name}")

            except ClientError as e:
                error_count += 1
                error_info = e.response.get("Error", {})
                if "Code" in error_info and "Message" in error_info:
                    logger.error(
                        f"AWS error processing {image_name}: {error_info['Code']} - "
                        f"{error_info['Message']}"
                    )
                else:
                    logger.error(f"AWS client error processing {image_name}: {str(e)}")
                continue
            except Exception as e:
                error_count += 1
                logger.error(f"Unexpected error processing {image_name}: {str(e)}")
                continue

        logger.info(f"Processing completed!")
        logger.info(f"Successfully processed: {processed_count} images")
        logger.info(f"Errors: {error_count} images")

    except Exception as e:
        logger.error(f"Script failed: {e}")
        raise


if __name__ == "__main__":
    process_existing_images()
