#!/bin/bash
set -e
sam build --use-container
sam deploy --force-upload --resolve-s3 --stack-name "image-labeling-stack" --capabilities CAPABILITY_IAM $@
