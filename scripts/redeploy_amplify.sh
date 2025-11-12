#!/bin/bash

set -e

STACK_NAME="image-labeling-stack"
BRANCH_NAME="${1:-main}"

echo "Getting Amplify App ID..."
APP_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
  --query "Stacks[0].Resources[?LogicalResourceId=='AmplifyApp'].PhysicalResourceId" \
  --output text)

if [ -z "$APP_ID" ]; then
  echo "Error: Could not find Amplify App ID"
  exit 1
fi

echo "Triggering Amplify deployment for App ID: $APP_ID (branch: $BRANCH_NAME)"
aws amplify start-job --app-id "$APP_ID" --branch-name "$BRANCH_NAME" --job-type RELEASE

echo "Deployment triggered successfully!"
