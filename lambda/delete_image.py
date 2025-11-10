"""
Lambda function to delete an image and its associated labels.
"""

import json
import boto3
import logging
import os
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def delete_image_labels(table, filename):
    """
    Delete all label entries for an image from DynamoDB.
    
    Args:
        table: DynamoDB table resource
        filename: Name of the image file
        
    Returns:
        int: Number of labels deleted
        
    Raises:
        ClientError: If DynamoDB operation fails
    """
    logger.debug(f"Querying DynamoDB for labels of image: {filename}")
    response = table.query(
        KeyConditionExpression='image_name = :img',
        ExpressionAttributeValues={':img': filename}
    )
    
    labels_count = len(response['Items'])
    logger.info(f"Found {labels_count} label entries to delete")
    
    if labels_count > 0:
        with table.batch_writer() as batch:
            for item in response['Items']:
                batch.delete_item(
                    Key={
                        'image_name': item['image_name'],
                        'label_name': item['label_name']
                    }
                )
        logger.info(f"Successfully deleted {labels_count} label entries from DynamoDB")
    else:
        logger.info("No label entries found to delete")
    
    return labels_count


def delete_image_from_s3(s3_client, bucket_name, filename):
    """
    Delete an image from S3.
    
    Args:
        s3_client: S3 client
        bucket_name: Name of the S3 bucket
        filename: Name of the image file
        
    Raises:
        ClientError: If S3 operation fails (except NoSuchKey)
    """
    s3_key = f"uploads/{filename}"
    logger.debug(f"Deleting S3 object: {s3_key} from bucket: {bucket_name}")
    
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
        logger.info(f"Successfully deleted image from S3: {s3_key}")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'NoSuchKey':
            logger.warning(f"Image {filename} not found in S3, but continuing with success")
        else:
            raise

def lambda_handler(event, context):
    """
    Delete an image and its associated labels from DynamoDB and S3.
    
    Args:
        event: API Gateway event containing the filename
        context: Lambda context object
        
    Returns:
        dict: Response with status code and message
    """
    logger.debug(f"Lambda invoked with event: {json.dumps(event)}")
    
    try:
        # Get filename from path parameters
        path_params = event.get('pathParameters') or {}
        filename = path_params.get('filename')
        if not filename:
            logger.warning("Delete request missing filename parameter")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Filename is required'})
            }
        
        logger.info(f"Starting deletion process for image: {filename}")
        
        # Validate bucket name from environment
        bucket_name = os.environ.get('BUCKET_NAME')
        if not bucket_name:
            logger.error("BUCKET_NAME environment variable not set")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Server configuration error'})
            }
        
        # Initialize AWS clients
        try:
            dynamodb = boto3.resource('dynamodb')
            s3_client = boto3.client('s3')
            table = dynamodb.Table('image_labels')
            logger.debug("AWS clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to initialize AWS services'})
            }
        
        # First, delete all label entries for this image from DynamoDB
        try:
            labels_count = delete_image_labels(table, filename)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"DynamoDB error ({error_code}): {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'Failed to delete labels: {error_code}'})
            }
        
        # Then delete the image from S3
        try:
            delete_image_from_s3(s3_client, bucket_name, filename)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"S3 error ({error_code}): {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'Failed to delete image from S3: {error_code}'})
            }
        
        logger.info(f"Image deletion completed successfully for: {filename}")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Image {filename} deleted successfully',
                'deleted_labels': labels_count
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error during image deletion: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }