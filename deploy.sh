#!/bin/bash
# Deployment script for the Image Labeling CloudFormation stack
# This script deploys the CloudFormation template to AWS

set -e

STACK_NAME="image-labeling-stack"
TEMPLATE_FILE="cloudformation-template.yaml"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

echo "Deploying Image Labeling CloudFormation stack..."
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo ""

# Check if stack exists
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "Stack exists. Updating stack..."
    aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-body "file://$TEMPLATE_FILE" \
        --capabilities CAPABILITY_IAM \
        --region "$REGION"
    
    echo "Waiting for stack update to complete..."
    aws cloudformation wait stack-update-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION"
else
    echo "Stack does not exist. Creating new stack..."
    aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-body "file://$TEMPLATE_FILE" \
        --capabilities CAPABILITY_IAM \
        --region "$REGION"
    
    echo "Waiting for stack creation to complete..."
    aws cloudformation wait stack-create-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION"
fi

echo ""
echo "Stack deployed successfully!"
echo ""

# Display stack outputs
echo "Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo "You can now upload images to: s3://bluestone-image-labeling-a08324be2c5f/uploads/"
echo "Labels will be saved to: s3://bluestone-image-labeling-a08324be2c5f/labels/"
