#!/bin/bash
set -e
sam build --use-container
sam deploy --force-upload --resolve-s3 --stack-name "image-labeling-stack" --capabilities CAPABILITY_IAM --parameter-overrides ForceUpdate=$(date +%s) $@

# Configure S3 notifications after successful deployment
echo "Configuring S3 notifications..."
./scripts/configure_s3_notifications.sh
