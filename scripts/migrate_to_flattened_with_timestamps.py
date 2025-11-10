#!/usr/bin/env python3
"""
Migration script to convert existing DynamoDB records to flattened schema.
This script reads existing image_labels records with nested labels and converts them
to the new flattened schema with composite keys.
"""

import boto3
import logging
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_to_flattened_schema():
    """Migrate existing nested labels to flattened schema"""

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("image_labels")

    logger.info("Starting migration to flattened schema...")

    try:
        # Scan all existing records
        response = table.scan()
        items = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        logger.info(f"Found {len(items)} existing records")

        migrated_count = 0
        deleted_count = 0

        for item in items:
            image_name = item.get("image_name", "")

            # Skip if this is already a flattened record (has label_name as sort key)
            if "label_name" in item and not image_name.startswith("label#"):
                logger.debug(f"Skipping already flattened record: {image_name}")
                continue

            # Skip old label# records
            if image_name.startswith("label#"):
                # Delete old label records
                try:
                    table.delete_item(Key={"image_name": image_name})
                    deleted_count += 1
                    logger.debug(f"Deleted old label record: {image_name}")
                except Exception as e:
                    logger.error(f"Failed to delete old record {image_name}: {e}")
                continue

            labels = item.get("labels", [])
            timestamp = item.get("timestamp", "")

            logger.info(f"Migrating {len(labels)} labels for image: {image_name}")

            # Create flattened label records
            for label in labels:
                label_name = label.get("name", "").lower()
                confidence = label.get("confidence", 0)

                # Ensure confidence is Decimal
                if not isinstance(confidence, Decimal):
                    confidence = Decimal(str(confidence))

                flattened_record = {
                    "image_name": image_name,
                    "label_name": label_name,
                    "confidence": confidence,
                }

                try:
                    table.put_item(Item=flattened_record)
                    logger.debug(f"Created flattened record: {image_name}#{label_name}")
                except Exception as e:
                    logger.error(
                        f"Failed to create flattened record for {image_name}/{label_name}: {e}"
                    )

            # Delete old nested record
            try:
                table.delete_item(Key={"image_name": image_name})
                logger.debug(f"Deleted old nested record: {image_name}")
            except Exception as e:
                logger.error(f"Failed to delete old record {image_name}: {e}")

            migrated_count += 1

        logger.info(f"Migration completed successfully!")
        logger.info(f"Migrated: {migrated_count} image records")
        logger.info(f"Deleted: {deleted_count} old label records")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate_to_flattened_schema()
