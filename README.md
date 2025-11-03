# Image Labelling

An AWS cloud application for automatic image labeling using Amazon Rekognition.

## Overview

This project provides an AWS CloudFormation template that creates:
- An S3 bucket (`bluestone-image-labeling-a08324be2c5f`) for storing images and labels
- A Lambda function (`bluestone_label_image`) that automatically labels images using Amazon Rekognition
- Automatic triggering when images are uploaded to the `uploads/` folder in the S3 bucket

## Architecture

1. **S3 Bucket**: Stores uploaded images and generated label files
   - Upload images to: `s3://bluestone-image-labeling-a08324be2c5f/uploads/`
   - Labels are saved to: `s3://bluestone-image-labeling-a08324be2c5f/labels/`

2. **Lambda Function**: Processes images automatically
   - Triggered on image upload (`.jpg`, `.jpeg`, `.png` files)
   - Uses Amazon Rekognition to detect labels
   - Saves results as JSON files in the S3 bucket

3. **IAM Role**: Provides necessary permissions for Lambda to access S3 and Rekognition

## Deployment

### Prerequisites
- AWS CLI configured with appropriate credentials
- AWS account with permissions to create CloudFormation stacks, S3 buckets, Lambda functions, and IAM roles

### Deploy the Stack

```bash
aws cloudformation create-stack \
  --stack-name image-labeling-stack \
  --template-body file://cloudformation-template.yaml \
  --capabilities CAPABILITY_IAM
```

### Check Deployment Status

```bash
aws cloudformation describe-stacks --stack-name image-labeling-stack
```

### Delete the Stack

```bash
aws cloudformation delete-stack --stack-name image-labeling-stack
```

Note: You may need to empty the S3 bucket before deletion.

## Usage

1. Upload an image to the S3 bucket under the `uploads/` folder:
   ```bash
   aws s3 cp your-image.jpg s3://bluestone-image-labeling-a08324be2c5f/uploads/your-image.jpg
   ```

2. The Lambda function will automatically process the image and save labels to:
   ```
   s3://bluestone-image-labeling-a08324be2c5f/labels/your-image.json
   ```

3. Retrieve the labels:
   ```bash
   aws s3 cp s3://bluestone-image-labeling-a08324be2c5f/labels/your-image.json ./labels.json
   cat labels.json
   ```

## Label Output Format

The Lambda function generates JSON files with the following structure:

```json
{
  "image": "uploads/your-image.jpg",
  "timestamp": "2024-11-03T13:45:30.123456",
  "labels": [
    {
      "name": "Dog",
      "confidence": 98.5
    },
    {
      "name": "Pet",
      "confidence": 97.3
    }
  ]
}
```

## Files

- `cloudformation-template.yaml`: CloudFormation template defining all AWS resources
- `lambda_function.py`: Python code for the Lambda function (also embedded in the template)

## Configuration

The Lambda function is configured with:
- **Runtime**: Python 3.11
- **Timeout**: 60 seconds
- **Memory**: 512 MB
- **Max Labels**: 10
- **Min Confidence**: 75%

These can be modified in the CloudFormation template if needed.
