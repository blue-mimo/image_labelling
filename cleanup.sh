#!/bin/bash
# Cleanup script for the Image Labeling CloudFormation stack
# This script removes the CloudFormation stack and all associated resources

set -e

STACK_NAME="image-labeling-stack"
BUCKET_NAME="bluestone-image-labeling-a08324be2c5f"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

echo "Cleaning up Image Labeling CloudFormation stack..."
echo "Stack Name: $STACK_NAME"
echo "Bucket Name: $BUCKET_NAME"
echo "Region: $REGION"
echo ""

# Empty the S3 bucket first (required before deletion)
echo "Emptying S3 bucket..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" --region "$REGION" 2>/dev/null; then
    aws s3 rm "s3://$BUCKET_NAME" --recursive --region "$REGION"
    echo "S3 bucket emptied."
else
    echo "S3 bucket does not exist or is not accessible."
fi

echo ""

# Delete the CloudFormation stack
echo "Deleting CloudFormation stack..."
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" >/dev/null 2>&1; then
    aws cloudformation delete-stack \
        --stack-name "$STACK_NAME" \
        --region "$REGION"
    
    echo "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION"
    
    echo "Stack deleted successfully!"
else
    echo "Stack does not exist."
fi

echo ""
echo "Cleanup complete!"
