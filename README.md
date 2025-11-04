# Image Labelling

An AWS cloud application for automatic image labeling using Amazon Rekognition.

## Overview

This project provides an AWS CloudFormation template that creates:
- An S3 bucket (`bluestone-image-labeling-a08324be2c5f`) for storing images and labels
  - Note: The bucket name uses hyphens instead of underscores because AWS S3 naming requirements only allow lowercase letters, numbers, hyphens, and periods
- A Lambda function (`process_added_image`) that automatically labels images using Amazon Rekognition
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
- AWS SAM CLI installed (`pip install aws-sam-cli`)
- AWS account with permissions to create CloudFormation stacks, S3 buckets, Lambda functions, and IAM roles

### Quick Deployment

```bash
sam deploy --guided
```

For subsequent deployments:

```bash
sam deploy
```

### Check Deployment Status

```bash
aws cloudformation describe-stacks --stack-name image-labeling-stack
```

### Delete the Stack

```bash
sam delete --stack-name image-labeling-stack
```

### Local Development

```bash
# Test API locally
sam local start-api

# Test specific Lambda function
sam local invoke ListImagesFunction
```

## Usage

### Web Application

After deployment, access the web application via the Amplify URL (shown in stack outputs):
- View uploaded images
- See generated labels for each image
- Upload new images through the S3 bucket

### API Endpoints

- **List Images**: `GET /images`
- **Get Labels**: `GET /labels/{filename}`

### Manual Upload

```bash
# Upload an image
aws s3 cp your-image.jpg s3://bluestone-image-labeling-a08324be2c5f/uploads/your-image.jpg

# Labels are automatically generated and saved to:
# s3://bluestone-image-labeling-a08324be2c5f/labels/your-image.json
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

- `template.yaml`: AWS SAM template defining all AWS resources
- `lambda/`: Directory containing Lambda function code
  - `process_added_image.py`: Processes uploaded images with Rekognition
  - `list_images.py`: Lists images from S3 uploads folder
  - `get_labels.py`: Retrieves labels for specific images
  - `test_*.py`: Unit tests for Lambda functions
- `web/`: Web application files
  - `index.html`: Frontend interface
  - `config.js`: Configuration file (updated during build)
- `.codecatalyst/`: CodeCatalyst CI/CD workflows

## Configuration

The Lambda function is configured with:
- **Runtime**: Python 3.11
- **Timeout**: 60 seconds
- **Memory**: 512 MB
- **Max Labels**: 10
- **Min Confidence**: 75%

These can be modified in the CloudFormation template if needed.
