#!/bin/bash
# Example usage script for the Image Labeling application
# This script demonstrates how to upload an image and retrieve labels

set -e

BUCKET_NAME="bluestone-image-labeling-a08324be2c5f"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <image-file>"
    echo "Example: $0 my-photo.jpg"
    exit 1
fi

IMAGE_FILE="$1"

if [ ! -f "$IMAGE_FILE" ]; then
    echo "Error: File '$IMAGE_FILE' not found!"
    exit 1
fi

# Get the base name of the file
IMAGE_NAME=$(basename "$IMAGE_FILE")

echo "Uploading image to S3..."
aws s3 cp "$IMAGE_FILE" "s3://$BUCKET_NAME/uploads/$IMAGE_NAME" --region "$REGION"
echo "Upload complete!"

echo ""
echo "Waiting for Lambda function to process the image (5 seconds)..."
sleep 5

# Get the label file name
LABEL_NAME="${IMAGE_NAME%.*}.json"

echo ""
echo "Retrieving labels..."
if aws s3 cp "s3://$BUCKET_NAME/labels/$LABEL_NAME" - --region "$REGION" 2>/dev/null; then
    echo ""
    echo "Labels retrieved successfully!"
else
    echo "Labels not yet available. The Lambda function may still be processing."
    echo "You can manually check with:"
    echo "aws s3 cp s3://$BUCKET_NAME/labels/$LABEL_NAME ./labels.json"
fi

echo ""
echo "Done!"
