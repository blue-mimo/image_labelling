#!/bin/bash
set -e

STACK_NAME="image-labeling-stack"
BUCKET_NAME="bluestone-image-labeling-a08324be2c5f"

echo "Configuring S3 notifications for Lambda function..."

# Get Lambda ARN from stack outputs
LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionArn`].OutputValue' \
  --output text)

if [ -z "$LAMBDA_ARN" ]; then
  echo "Error: Could not retrieve Lambda function ARN from stack outputs"
  exit 1
fi

echo "Lambda ARN: $LAMBDA_ARN"

# Verify Lambda function exists
echo "Verifying Lambda function exists..."
aws lambda get-function --function-name process_added_image > /dev/null
if [ $? -ne 0 ]; then
  echo "Error: Lambda function 'process_added_image' does not exist"
  exit 1
fi
echo "Lambda function verified"

# Add Lambda permission for S3 to invoke the function
aws lambda add-permission \
  --function-name process_added_image \
  --principal s3.amazonaws.com \
  --action lambda:InvokeFunction \
  --source-arn "arn:aws:s3:::$BUCKET_NAME" \
  --statement-id s3-invoke-lambda || echo "Permission already exists"

# Configure S3 bucket notifications
echo "Configuring S3 bucket notifications..."
aws s3api put-bucket-notification-configuration \
  --bucket $BUCKET_NAME \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "Id": "ProcessImages",
      "LambdaFunctionArn": "'$LAMBDA_ARN'",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {"Name": "prefix", "Value": "uploads/"}
          ]
        }
      }
    }]
  }'

echo "S3 notifications configured successfully!"