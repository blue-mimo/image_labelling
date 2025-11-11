#!/usr/bin/env python3
"""
Script to initialize the label_counts table from existing image_labels data.
"""

import boto3
from collections import Counter

def initialize_label_counts():
    """Initialize label_counts table from image_labels table."""
    dynamodb = boto3.resource('dynamodb')
    
    labels_table = dynamodb.Table('image_labels')
    counts_table = dynamodb.Table('label_counts')
    
    print("Scanning image_labels table...")
    
    # Scan all items from image_labels table
    response = labels_table.scan()
    items = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = labels_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    print(f"Found {len(items)} label entries")
    
    # Count occurrences of each label
    label_counts = Counter(item['label_name'] for item in items)
    
    print(f"Found {len(label_counts)} unique labels")
    
    # Write counts to label_counts table
    with counts_table.batch_writer() as batch:
        for label_name, count in label_counts.items():
            batch.put_item(Item={
                'label_name': label_name,
                'count': count
            })
    
    print(f"Initialized label_counts table with {len(label_counts)} entries")

if __name__ == '__main__':
    initialize_label_counts()