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
        logger.debug(f"Event: {json.dumps(event, default=str)[:500]}...")

        if event.get("httpMethod") == "OPTIONS":
            logger.debug("Handling OPTIONS request")
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            }

        logger.debug("Extracting file data from request")
        file_data, filename, file_ext = get_file_name_and_data(event)
        logger.debug(
            f"Extracted file: {filename}, extension: {file_ext}, size: {len(file_data)} bytes"
        )

        s3_key = upload_image_to_s3(file_data, filename, file_ext)

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


def upload_image_to_s3(file_data, filename, file_ext):
    """Upload image data to S3 bucket"""
    s3_key = f"uploads/{filename}"
    logger.debug(
        f"Uploading to S3: bucket={BUCKET_NAME}, key={s3_key}, content_type={_CONTENT_MAPPING[file_ext]}"
    )

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=file_data,
        ContentType=_CONTENT_MAPPING[file_ext],
    )

    logger.info(f"Successfully uploaded {filename} to {BUCKET_NAME}/{s3_key}")
    return s3_key


def get_file_name_and_data(event):
    """Extract filename and file data from multipart form data"""
    logger.debug("Extracting file data from request")

    content_type = event.get("headers", {}).get("content-type", "")
    logger.debug(f"Content-Type: {content_type}")

    if "multipart/form-data" not in content_type:
        logger.error(f"Invalid content type: {content_type}")
        raise HTTPClientError(400, "Content-Type must be multipart/form-data")

    body = decode_request_body(event)

    # Extract file from multipart data
    logger.debug("Parsing multipart data")
    file_data, filename = parse_multipart_data(body, content_type)

    if not file_data or not filename:
        logger.error("No file found in request")
        raise HTTPClientError(400, "No file provided")

    logger.debug(f"Parsed file: {filename}, data length: {len(file_data)}")
    logger.debug(
        f"First 20 bytes: {file_data[:20].hex() if len(file_data) >= 20 else file_data.hex()}"
    )

    # Validate file extension
    file_ext = os.path.splitext(filename.lower())[1]
    logger.debug(f"File extension: {file_ext}")

    if file_ext not in _CONTENT_MAPPING:
        logger.error(f"Invalid file extension: {file_ext}")
        raise HTTPClientError(400, f"File type {file_ext} not allowed")

    logger.debug(
        f"Extracted file: {filename}, extension: {file_ext}, size: {len(file_data)} bytes"
    )

    return file_data, filename, file_ext


def decode_request_body(event):
    body = event.get("body", "")
    is_base64 = event.get("isBase64Encoded", False)
    logger.debug(f"Body length: {len(body)}, isBase64Encoded: {is_base64}")

    if is_base64:
        body = base64.b64decode(body)
        logger.debug(f"Decoded body length: {len(body)}")
    else:
        body = body.encode("latin1")
        logger.debug(f"Encoded body length: {len(body)}")
    return body


def parse_multipart_data(body, content_type):
    """Parse multipart form data to extract file"""
    try:
        # Extract boundary from content-type
        boundary = content_type.split("boundary=")[1].encode()
        logger.debug(f"Boundary: {boundary}")

        # Split by boundary
        parts = body.split(b"--" + boundary)
        logger.debug(f"Found {len(parts)} parts")

        for part in parts:
            if b"Content-Disposition: form-data" in part and b"filename=" in part:
                # Extract filename
                filename = None
                lines = part.split(b"\r\n")
                logger.debug(f"Part has {len(lines)} lines")
                for line in lines:
                    if b"filename=" in line:
                        filename = line.split(b'filename="')[1].split(b'"')[0].decode()
                        logger.debug(f"Found filename: {filename}")
                        break

                # Extract file data (after double CRLF)
                data_start = part.find(b"\r\n\r\n") + 4
                data_end = part.rfind(b"\r\n")
                logger.debug(f"Data boundaries: start={data_start}, end={data_end}")

                if data_end > data_start:
                    file_data = part[data_start:data_end]
                else:
                    file_data = part[data_start:]

                logger.debug(f"Extracted {len(file_data)} bytes of file data")
                return file_data, filename

        return None, None

    except Exception as e:
        logger.error(f"Error parsing multipart data: {e}")
        return None, None
