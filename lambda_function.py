"""
Lambda function for automatic image labeling using Amazon Rekognition.
This function is triggered when an image is uploaded to the S3 bucket.
"""

import json
import boto3
import logging
from datetime import datetime
from urllib.parse import unquote_plus

# Initialize AWS clients
s3_client = boto3.client('s3')
rekognition_client = boto3.client('rekognition')

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
        # Parse the S3 event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            
            logger.info(f'Processing image: {key} from bucket: {bucket}')
            
            # Call Amazon Rekognition to detect labels
            response = rekognition_client.detect_labels(
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
                'timestamp': datetime.utcnow().isoformat(),
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
            
            s3_client.put_object(
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
