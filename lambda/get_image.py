import base64
import boto3

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"
s3_client = boto3.client("s3")

_CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
}


def lambda_handler(event, context):
    try:
        image_filename = event["pathParameters"]["filename"]

        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=f"uploads/{image_filename}")
        image_data = obj["Body"].read()

        extension = image_filename[image_filename.rfind(".") :].lower()
        content_type = _CONTENT_TYPE_MAP[extension]

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
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": f'{{"error": "{str(e)}"}}',
        }
