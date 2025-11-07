import json
import boto3
import logging
from urllib.parse import unquote

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"
s3_client = boto3.client("s3")


def lambda_handler(event, context):
    logger.debug(f"List images invoked with event: {json.dumps(event)}")
    
    # Parse query parameters
    query_params = event.get("queryStringParameters") or {}
    page = int(query_params.get("page", 0))
    limit = int(query_params.get("limit", 12))
    filters = query_params.get("filters", "").split(",") if query_params.get("filters") else []
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
            filtered_images = []
            for image in all_images:
                try:
                    # Get labels for this image
                    label_key = f"labels/{image.rsplit('.', 1)[0]}.json"
                    label_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=label_key)
                    labels_data = json.loads(label_obj["Body"].read().decode("utf-8"))
                    
                    # Check if any filter matches any label
                    image_labels = [label["name"].lower() for label in labels_data.get("labels", [])]
                    if any(any(filter_term in label for label in image_labels) for filter_term in filters):
                        filtered_images.append(image)
                except Exception as e:
                    logger.warning(f"Could not get labels for {image}: {e}")
                    continue
            images = filtered_images
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
                "totalPages": (total_count + limit - 1) // limit
            }
        }
        
        logger.info(f"Returning {len(page_images)} images (page {page} of {result['pagination']['totalPages']})")
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
