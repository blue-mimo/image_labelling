import base64
import boto3
import json
import logging
import io
from PIL import Image


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"
s3_client = boto3.client("s3")

_CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
}


def lambda_handler(event, context):
    logger.debug(f"Get image invoked with event: {json.dumps(event)}")

    if "pathParameters" not in event or "filename" not in event["pathParameters"]:
        logger.error("Filename not provided in path parameters")
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": '{"error": "Filename not provided"}',
        }

    image_filename = event["pathParameters"]["filename"]

    # Get scaling parameters
    query_params = event.get("queryStringParameters") or {}

    def safe_int(value):
        try:
            return int(value) if value else None
        except (ValueError, TypeError):
            return None

    max_width = safe_int(query_params.get("maxwidth"))
    max_height = safe_int(query_params.get("maxheight"))
    logger.info(f"Scaling parameters: max_width={max_width}, max_height={max_height}")

    try:
        logger.info(f"Getting image: {image_filename}")
        logger.debug(f"S3 key: uploads/{image_filename}")

        logger.debug("Calling S3 get_object for image")
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=f"uploads/{image_filename}")
        image_data = obj["Body"].read()
        logger.debug(f"Retrieved image data: {len(image_data)} bytes")

        # Validate image data
        if len(image_data) == 0:
            raise ValueError("Image file is empty")

        # Check for common image file signatures
        if image_data[:2] == b"\xff\xd8":  # JPEG
            logger.debug("Detected JPEG image")
        elif image_data[:8] == b"\x89PNG\r\n\x1a\n":  # PNG
            logger.debug("Detected PNG image")
        elif image_data[:6] in [b"GIF87a", b"GIF89a"]:  # GIF
            logger.debug("Detected GIF image")
        else:
            logger.warning(f"Unknown image format, first 10 bytes: {image_data[:10]}")

        extension = (
            image_filename[image_filename.rfind(".") :].lower()
            if "." in image_filename
            else ""
        )
        if not extension:
            raise RuntimeError(
                "No file extension found, defaulting content type to application/octet-stream"
            )
        elif extension not in _CONTENT_TYPE_MAP:
            raise RuntimeError(f"Unrecognized file extension: {extension}")

        content_type = _CONTENT_TYPE_MAP[extension]
        logger.debug(f"Content type for {extension}: {content_type}")

        # Scale image if parameters provided
        if max_width or max_height:
            logger.info(f"Starting image scaling for {image_filename}")
            original_size = len(image_data)
            image_data = scale_image(image_data, max_width, max_height, content_type)
            logger.info(
                f"Image scaling complete: {original_size} -> {len(image_data)} bytes"
            )
        else:
            logger.debug("No scaling parameters provided, returning original image")

        # Validate base64 encoding
        encoded_data = base64.b64encode(image_data).decode("utf-8")
        logger.debug(f"Base64 encoded length: {len(encoded_data)} characters")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": content_type,
                "Access-Control-Allow-Origin": "*",
            },
            "body": encoded_data,
            "isBase64Encoded": True,
        }
    except Exception as e:
        logger.error(f"Error getting image {image_filename}: {str(e)}")
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": f'{{"error": "{str(e)}"}}',
        }


def scale_image(image_data, max_width, max_height, content_type):
    """Scale image proportionally to fit within max dimensions"""
    logger.debug(
        f"scale_image called with max_width={max_width}, max_height={max_height}, content_type={content_type}"
    )
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_data))

        # Handle EXIF orientation
        try:
            _EXIF_ORIENTATION_TAG = 274
            exif = image.getexif()
            orientation = int(exif.get(_EXIF_ORIENTATION_TAG, 1) if exif else 1)
            rotation = {1: 0, 3: 180, 6: 270, 8: 90}[orientation]
            logger.debug(f"EXIF orientation: {orientation}, rotation: {rotation}°")
        except (AttributeError, KeyError, TypeError) as e:
            rotation = 0
            logger.debug(f"No EXIF orientation data: {e}")

        dimension_swap = rotation in [90, 270]
        real_width = image.width if not dimension_swap else image.height
        real_height = image.height if not dimension_swap else image.width
        logger.debug(f"Original image dimensions: {real_width}x{real_height}")

        scale_x = max_width / real_width if max_width else float("inf")
        scale_y = max_height / real_height if max_height else float("inf")
        scale = min(scale_x, scale_y, 1.0)  # Don't upscale

        if scale >= 1.0:
            logger.debug(f"No scaling needed (scale={scale:.3f})")
            return image_data  # No scaling needed

        logger.debug(f"Scaling factor: {scale:.3f}")

        if rotation:
            logger.debug(f"Rotating image by {rotation}°")
            image = image.rotate(rotation, expand=True)

        new_width = int(real_width * scale)
        new_height = int(real_height * scale)
        logger.debug(f"Resizing to: {new_width}x{new_height}")
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert back to bytes
        output = io.BytesIO()
        pil_format = content_type.split("/")[-1].upper()
        logger.debug(f"Saving image as {pil_format} format")
        image.save(
            output, format=pil_format, quality=85 if pil_format == "JPEG" else None
        )
        result = output.getvalue()
        logger.debug(f"Final scaled image size: {len(result)} bytes")
        return result

    except Exception as e:
        logger.error(f"Error scaling image: {str(e)}")
        return image_data  # Return original if scaling fails
