#!/bin/bash
# Deployment script for the Image Labeling CloudFormation stack
# This script deploys the CloudFormation template to AWS

set -e

STACK_NAME="image-labeling-stack"
TEMPLATE_FILE="template.yaml"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

echo "Deploying Image Labeling CloudFormation stack..."
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo ""

# Function to create stack and wait for completion
create_stack() {
    echo "Creating new stack..."
    sam deploy \
        --template-file "$TEMPLATE_FILE" \
        --stack-name "$STACK_NAME" \
        --capabilities CAPABILITY_IAM \
        --region "$REGION" \
        --resolve-s3
}

# Function to update stack and wait for completion
update_stack() {
    echo "Stack exists. Updating stack..."
    sam deploy \
        --template-file "$TEMPLATE_FILE" \
        --stack-name "$STACK_NAME" \
        --capabilities CAPABILITY_IAM \
        --region "$REGION" \
        --resolve-s3
}

# Function to delete stack and wait for completion
delete_stack() {
    echo "Stack is in ROLLBACK_COMPLETE state. Deleting and recreating..."
    aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"
}

# Check if stack exists and get its status
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackStatus' --output text 2>/dev/null)

if [ $? -eq 0 ]; then
    if [ "$STACK_STATUS" = "ROLLBACK_COMPLETE" ]; then
        delete_stack
        create_stack
    else
        update_stack
    fi
else
    create_stack
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
