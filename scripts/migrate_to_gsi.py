#!/usr/bin/env python3
"""
Migration script to add individual label records for GSI querying.
This script reads existing image_labels records and creates individual label records
for efficient querying by label names.
"""

import boto3
import logging
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_labels_to_gsi():
    """Migrate existing labels to support GSI querying"""
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('image_labels')
    
    logger.info("Starting migration to GSI structure...")
    
    try:
        # Scan all existing records
        response = table.scan()
        items = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        logger.info(f"Found {len(items)} existing records")
        
        migrated_count = 0
        skipped_count = 0
        
        for item in items:
            image_name = item.get('image_name', '')
            
            # Skip if this is already a label record
            if image_name.startswith('label#'):
                skipped_count += 1
                continue
                
            labels = item.get('labels', [])
            timestamp = item.get('timestamp', '')
            
            logger.info(f"Migrating {len(labels)} labels for image: {image_name}")
            
            # Create individual label records
            for label in labels:
                label_name = label.get('name', '').lower()
                confidence = label.get('confidence', 0)
                
                # Ensure confidence is Decimal
                if not isinstance(confidence, Decimal):
                    confidence = Decimal(str(confidence))
                
                label_record = {
                    'image_name': f"label#{image_name}#{label_name}",
                    'label_name': label_name,
                    'original_image': image_name,
                    'confidence': confidence,
                    'timestamp': timestamp,
                }
                
                try:
                    table.put_item(Item=label_record)
                    logger.debug(f"Created label record: {label_name} for {image_name}")
                except Exception as e:
                    logger.error(f"Failed to create label record for {image_name}/{label_name}: {e}")
            
            migrated_count += 1
        
        logger.info(f"Migration completed successfully!")
        logger.info(f"Migrated: {migrated_count} image records")
        logger.info(f"Skipped: {skipped_count} existing label records")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == '__main__':
    migrate_labels_to_gsi()