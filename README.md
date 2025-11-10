# Image Labelling

An AWS cloud application for automatic image labeling using Amazon Rekognition.

## Overview

This project provides an AWS CloudFormation template that creates:
- An S3 bucket (`bluestone-image-labeling-a08324be2c5f`) for storing images and labels
  - Note: The bucket name uses hyphens instead of underscores because AWS S3 naming requirements only allow lowercase letters, numbers, hyphens, and periods
- A Lambda function (`process_added_image`) that automatically labels images using Amazon Rekognition
- Automatic triggering when images are uploaded to the `uploads/` folder in the S3 bucket

## Architecture

1. **S3 Bucket**: Stores uploaded images
   - Upload images to: `s3://bluestone-image-labeling-a08324be2c5f/uploads/`
   - Labels are stored in DynamoDB for efficient querying

2. **Lambda Function**: Processes images automatically
   - Triggered on image upload (`.jpg`, `.jpeg`, `.png` files)
   - Uses Amazon Rekognition to detect labels
   - Saves results to DynamoDB table with GSI for efficient querying

3. **DynamoDB Table**: Stores image labels with composite key and Global Secondary Index
   - Composite key: `image_name` (partition key) + `label_name` (sort key)
   - GSI: `label-index` with `label_name` as key for efficient filtering
   - Flattened schema eliminates redundancy and enables fast queries

4. **IAM Role**: Provides necessary permissions for Lambda to access S3, Rekognition, and DynamoDB

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

# Labels are automatically generated and saved to DynamoDB
# Query labels using the API endpoints or DynamoDB console
```

## DynamoDB Structure

The Lambda function stores labels in DynamoDB using a flattened schema with composite keys:

**Label Records (one per label):**
```json
{
  "image_name": "your-image.jpg",
  "label_name": "dog",
  "confidence": 98.5
}
```

**Key Structure:**
- **Partition Key**: `image_name` (e.g., "your-image.jpg")
- **Sort Key**: `label_name` (e.g., "dog")
- **GSI**: `label-index` on `label_name` for filtering by labels

## Files

- `template.yaml`: AWS SAM template defining all AWS resources
- `lambda/`: Directory containing Lambda function code
  - `process_added_image.py`: Processes uploaded images with Rekognition, stores in DynamoDB
  - `list_images.py`: Lists images with DynamoDB-based filtering
  - `get_labels.py`: Retrieves labels for specific images from DynamoDB
  - `test_*.py`: Unit tests for Lambda functions
- `scripts/`: Migration and utility scripts
  - `migrate_to_flattened_with_timestamps.py`: Migrates from nested to flattened schema (legacy)
  - `migrate_remove_timestamps.py`: Removes timestamps from existing flattened records
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
