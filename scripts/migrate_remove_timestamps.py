#!/usr/bin/env python3
"""
Migration script to remove timestamps from DynamoDB records.
This script migrates from the previous structure (full object + flattened with timestamps)
to the new simplified flattened structure without timestamps.
"""

import boto3
import logging
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_remove_timestamps():
    """Remove timestamps from existing DynamoDB records"""

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("image_labels")

    logger.info("Starting migration to remove timestamps...")

    try:
        # Scan all existing records
        response = table.scan()
        items = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        logger.info(f"Found {len(items)} existing records")

        updated_count = 0
        deleted_count = 0

        for item in items:
            image_name = item.get("image_name", "")

            # Handle old full object records (have 'labels' array)
            if "labels" in item:
                labels = item.get("labels", [])

                logger.info(
                    f"Converting full object record for image: {image_name} with {len(labels)} labels"
                )

                # First delete the old full object record to avoid conflicts
                try:
                    table.delete_item(Key={"image_name": image_name})
                    deleted_count += 1
                    logger.debug(f"Deleted old full object record: {image_name}")
                except Exception as e:
                    logger.error(f"Failed to delete old record {image_name}: {e}")
                    continue

                # Then create new flattened records without timestamp
                for label in labels:
                    label_name = label.get("name", "").lower()
                    confidence = label.get("confidence", 0)

                    # Ensure confidence is Decimal
                    if not isinstance(confidence, Decimal):
                        confidence = Decimal(str(confidence))

                    new_record = {
                        "image_name": image_name,
                        "label_name": label_name,
                        "confidence": confidence,
                    }

                    try:
                        table.put_item(Item=new_record)
                        logger.debug(f"Created new record: {image_name}#{label_name}")
                    except Exception as e:
                        logger.error(
                            f"Failed to create record for {image_name}/{label_name}: {e}"
                        )

            # Handle old label# records
            elif image_name.startswith("label#"):
                # Delete old label# records (only has partition key)
                try:
                    table.delete_item(Key={"image_name": image_name})
                    deleted_count += 1
                    logger.debug(f"Deleted old label# record: {image_name}")
                except Exception as e:
                    logger.error(
                        f"Failed to delete old label# record {image_name}: {e}"
                    )

            # Handle existing flattened records with timestamps
            elif "label_name" in item and "timestamp" in item:
                label_name = item.get("label_name", "")
                confidence = item.get("confidence", 0)

                # Ensure confidence is Decimal
                if not isinstance(confidence, Decimal):
                    confidence = Decimal(str(confidence))

                # Create new record without timestamp
                new_record = {
                    "image_name": image_name,
                    "label_name": label_name,
                    "confidence": confidence,
                }

                try:
                    # For composite key table, we can just put the new item (it will overwrite)
                    table.put_item(Item=new_record)
                    updated_count += 1
                    logger.debug(f"Updated record: {image_name}#{label_name}")
                except Exception as e:
                    logger.error(
                        f"Failed to update record {image_name}/{label_name}: {e}"
                    )

            # Skip records that are already in the correct format
            elif "label_name" in item and "timestamp" not in item:
                logger.debug(
                    f"Skipping already migrated record: {image_name}#{item.get('label_name', '')}"
                )
                continue

        logger.info(f"Migration completed successfully!")
        logger.info(f"Updated: {updated_count} records (removed timestamps)")
        logger.info(f"Deleted: {deleted_count} old records")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate_remove_timestamps()
