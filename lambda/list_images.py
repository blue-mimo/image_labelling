import json
import boto3
import logging
from urllib.parse import unquote

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("image_labels")


def lambda_handler(event, context):
    logger.debug(f"List images invoked with event: {json.dumps(event)}")

    # Parse query parameters
    query_params = event.get("queryStringParameters") or {}
    page = int(query_params.get("page", 0))
    limit = int(query_params.get("limit", 10))
    filters = (
        query_params.get("filters", "").split(",")
        if query_params.get("filters")
        else []
    )
    filters = [f.strip().lower() for f in filters if f.strip()]

    logger.info(f"Request params - page: {page}, limit: {limit}, filters: {filters}")

    try:
        # Get all images
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="uploads/")
        keys = [obj["Key"] for obj in response.get("Contents", []) if "Key" in obj]
        all_images = [
            key.replace("uploads/", "")
            for key in keys
            if key != "uploads/" and key.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        # Apply filters if provided
        if filters:
            # Use DynamoDB GSI to query by labels
            filtered_images = set()
            for filter_term in filters:
                try:
                    response = table.query(
                        IndexName="label-index",
                        KeyConditionExpression="label_name = :label",
                        ExpressionAttributeValues={":label": filter_term},
                    )

                    # Extract image names from label records
                    for item in response.get("Items", []):
                        filtered_images.add(item["image_name"])

                except Exception as e:
                    logger.warning(
                        f"Could not query labels for filter '{filter_term}': {e}"
                    )

            # Filter S3 images to only include those with matching labels
            images = [img for img in all_images if img in filtered_images]
        else:
            images = all_images

        # Apply pagination
        total_count = len(images)
        start_index = page * limit
        end_index = start_index + limit
        page_images = images[start_index:end_index]

        result = {
            "images": page_images,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "totalPages": (total_count + limit - 1) // limit,
            },
        }

        logger.info(
            f"Returning {len(page_images)} images (page {page} of {result['pagination']['totalPages']})"
        )
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(result),
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
