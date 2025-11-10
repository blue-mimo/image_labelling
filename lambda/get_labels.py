import json
import boto3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('image_labels')


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
        logger.info(f"Getting labels for image: {filename}")
        logger.debug(f"DynamoDB key: {filename}")

        logger.debug("Calling DynamoDB get_item for labels")
        response = table.get_item(
            Key={'image_name': filename}
        )
        
        if 'Item' not in response:
            raise Exception(f"No labels found for image: {filename}")
            
        item = response['Item']
        labels = {
            'image': f"uploads/{filename}",
            'timestamp': item['timestamp'],
            'labels': item['labels']
        }
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
