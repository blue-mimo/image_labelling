#!/usr/bin/env python3
import boto3
import json
from decimal import Decimal

# Initialize clients
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("image_labels")

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"


def migrate_labels():
    # List all JSON files in labels/ folder
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="labels/")

    if "Contents" not in response:
        print("No label files found")
        return

    for obj in response["Contents"]:
        key = obj.get("Key", "")
        if not key.endswith(".json"):
            continue

        print(f"Migrating {key}")

        # Read JSON from S3
        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))

        # Extract image name from path
        image_name = data["image"].replace("uploads/", "")

        # Convert confidence values to Decimal
        labels = [
            {"name": label["name"], "confidence": Decimal(str(label["confidence"]))}
            for label in data["labels"]
        ]

        # Write to DynamoDB
        try:
            response = table.put_item(
                Item={
                    "image_name": image_name,
                    "timestamp": data["timestamp"],
                    "labels": labels,
                }
            )

            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                print(f"✓ Migrated {image_name}")
            else:
                print(
                    f"✗ Failed to migrate {image_name}: HTTP {response['ResponseMetadata']['HTTPStatusCode']}"
                )

        except Exception as e:
            print(f"✗ Error migrating {image_name}: {str(e)}")


if __name__ == "__main__":
    migrate_labels()
    print("Migration complete")
