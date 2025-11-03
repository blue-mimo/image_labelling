"""
Lambda function for automatic image labeling using Amazon Rekognition.
This function is triggered when an image is uploaded to the S3 bucket.
"""

import json
import boto3
import logging
from datetime import datetime, timezone
from urllib.parse import unquote_plus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients (will be set on first use or can be mocked for testing)
s3_client = None
rekognition_client = None


def get_s3_client():
    """Get or create S3 client."""
    global s3_client
    if s3_client is None:
        s3_client = boto3.client('s3')
    return s3_client


def get_rekognition_client():
    """Get or create Rekognition client."""
    global rekognition_client
    if rekognition_client is None:
        rekognition_client = boto3.client('rekognition')
    return rekognition_client


def lambda_handler(event, context):
    """
    Lambda function to label images using Amazon Rekognition.
    Triggered when an image is uploaded to the S3 bucket.
    
    Args:
        event: S3 event containing bucket and object information
        context: Lambda context object
        
    Returns:
        dict: Response with status code and message
    """
    try:
        # Get clients
        s3 = get_s3_client()
        rekognition = get_rekognition_client()
        
        # Parse the S3 event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            
            logger.info(f'Processing image: {key} from bucket: {bucket}')
            
            # Call Amazon Rekognition to detect labels
            response = rekognition.detect_labels(
                Image={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                },
                MaxLabels=10,
                MinConfidence=75
            )
            
            # Extract labels from the response
            labels = response['Labels']
            logger.info(f'Detected {len(labels)} labels')
            
            # Format the results
            results = {
                'image': key,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'labels': [
                    {
                        'name': label['Name'],
                        'confidence': round(label['Confidence'], 2)
                    }
                    for label in labels
                ]
            }
            
            # Save the labels to S3
            # Replace uploads/ with labels/ and change extension to .json
            label_key = key.replace('uploads/', 'labels/', 1)
            label_key = label_key.rsplit('.', 1)[0] + '.json'
            
            s3.put_object(
                Bucket=bucket,
                Key=label_key,
                Body=json.dumps(results, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f'Labels saved to: {label_key}')
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Image labeling completed successfully',
                'processed_images': len(event['Records'])
            })
        }
        
    except Exception as e:
        logger.error(f'Error processing image: {str(e)}')
        raise
