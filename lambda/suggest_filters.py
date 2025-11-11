"""
Lambda function to filter suggestions by prefix.
"""

import json
import logging
import boto3
from urllib.parse import unquote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("prefix_suggestions")


def lambda_handler(event, context):
    """
    Get suggestions for a given prefix.

    Args:
        event: API Gateway event with queryStringParameters
        context: Lambda context object

    Returns:
        dict: Response with suggestions list
    """
    try:
        prefix = event.get("queryStringParameters", {}).get("prefix", "")

        if not prefix:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing prefix parameter"}),
            }

        decoded_prefix = unquote_plus(prefix).lower()

        response = table.get_item(Key={"prefix": decoded_prefix})

        suggestions = (
            response["Item"].get("suggestions", []) if "Item" in response else []
        )

        return {
            "statusCode": 200,
            "body": json.dumps(suggestions),
        }

    except Exception as e:
        logger.error(f"Error filtering suggestions: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "details": str(e)}),
        }
