import json
import boto3

BUCKET_NAME = 'bluestone-image-labeling-a08324be2c5f'
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    try:
        filename = event['pathParameters']['filename']
        label_filename = filename.rsplit('.', 1)[0] + '.json'
        
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=f'labels/{label_filename}')
        labels = json.loads(obj['Body'].read().decode('utf-8'))
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(labels)
        }
    except Exception as e:
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }