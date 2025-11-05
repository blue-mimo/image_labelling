import json
import base64
import boto3
import logging
import os
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"
s3_client = boto3.client("s3")

_CONTENT_MAPPING = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
}


class HTTPClientError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def lambda_handler(event, context):
    """
    Lambda function to upload images to S3 bucket
    """
    try:
        logger.info("Upload image request received")

        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            }

        file_data, filename, file_ext = get_file_name_and_data(event)

        # Upload to S3
        s3_key = f"uploads/{filename}"

        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_data,
            ContentType=_CONTENT_MAPPING[file_ext],
        )

        logger.info(f"Successfully uploaded {filename} to {BUCKET_NAME}/{s3_key}")

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {
                    "message": "File uploaded successfully",
                    "filename": filename,
                    "s3_key": s3_key,
                }
            ),
        }
    except HTTPClientError as e:
        logger.error(f"Client error: {e.message}")
        return {
            "statusCode": e.status_code,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": e.message}),
        }
    except ClientError as e:
        logger.error(f"S3 error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Failed to upload to S3"}),
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Internal server error"}),
        }


def get_file_name_and_data(event):
    content_type = event.get("headers", {}).get("content-type", "")
    if "multipart/form-data" not in content_type:
        logger.error(f"Invalid content type: {content_type}")
        raise HTTPClientError(400, "Content-Type must be multipart/form-data")

    """Extract filename and file data from multipart form data"""
    # Decode base64 body
    body = event.get("body", "")
    if event.get("isBase64Encoded", False):
        body = base64.b64decode(body)
    else:
        body = body.encode("latin1")

    # Extract file from multipart data
    file_data, filename = parse_multipart_data(body, content_type)

    if not file_data or not filename:
        logger.error("No file found in request")
        raise HTTPClientError(400, "No file provided")

    # Validate file extension
    file_ext = os.path.splitext(filename.lower())[1]

    if file_ext not in _CONTENT_MAPPING:
        logger.error(f"Invalid file extension: {file_ext}")
        raise HTTPClientError(400, f"File type {file_ext} not allowed")

    return file_data, filename, file_ext


def parse_multipart_data(body, content_type):
    """Parse multipart form data to extract file"""
    try:
        # Extract boundary from content-type
        boundary = content_type.split("boundary=")[1].encode()

        # Split by boundary
        parts = body.split(b"--" + boundary)

        for part in parts:
            if b"Content-Disposition: form-data" in part and b"filename=" in part:
                # Extract filename
                filename = None
                lines = part.split(b"\r\n")
                for line in lines:
                    if b"filename=" in line:
                        filename = line.split(b'filename="')[1].split(b'"')[0].decode()
                        break

                # Extract file data (after double CRLF)
                data_start = part.find(b"\r\n\r\n") + 4
                data_end = part.rfind(b"\r\n")
                if data_end > data_start:
                    file_data = part[data_start:data_end]
                else:
                    file_data = part[data_start:]

                return file_data, filename

        return None, None

    except Exception as e:
        logger.error(f"Error parsing multipart data: {e}")
        return None, None
