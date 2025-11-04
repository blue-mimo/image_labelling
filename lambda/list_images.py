import json
import boto3

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"
s3_client = boto3.client("s3")


def lambda_handler(event, context):
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="uploads/")
        keys = [obj["Key"] for obj in response.get("Contents", []) if "Key" in obj]
        images = [
            key.replace("uploads/", "")
            for key in keys
            if key != "uploads/" and key.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(images),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }
