#!/bin/bash
set -e

echo "Deleting existing stack..."
sam delete --stack-name image-labeling-stack --no-prompts

echo "Waiting for stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name image-labeling-stack

echo "Deploying fresh stack..."
sam build --use-container
sam deploy --guided --stack-name image-labeling-stack

echo "Configuring S3 notifications..."
./scripts/configure_s3_notifications.sh

echo "Stack redeployment completed!"