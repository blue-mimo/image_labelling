"""
Unit tests for the Lambda function.
These tests verify the structure and logic without requiring AWS services.
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys

# Import the lambda function
import process_added_image


class TestLambdaFunction(unittest.TestCase):
    """Test cases for the image labeling Lambda function."""
    
    @patch('process_added_image.get_dynamodb_resource')
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_lambda_handler_success(self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb):
        """Test successful image labeling."""
        # Create mock clients
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock Rekognition response
        mock_rekognition.detect_labels.return_value = {
            'Labels': [
                {'Name': 'Dog', 'Confidence': 98.5},
                {'Name': 'Pet', 'Confidence': 97.3},
                {'Name': 'Animal', 'Confidence': 96.8}
            ]
        }
        
        # Mock DynamoDB put_item
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Create test event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': 'test-bucket'},
                        'object': {'key': 'uploads/test-image.jpg'}
                    }
                }
            ]
        }
        
        # Call the Lambda handler
        context = Mock()
        response = process_added_image.lambda_handler(event, context)
        
        # Verify the response
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'Image labeling completed successfully')
        self.assertEqual(body['processed_images'], 1)
        
        # Verify Rekognition was called with correct parameters
        mock_rekognition.detect_labels.assert_called_once_with(
            Image={
                'S3Object': {
                    'Bucket': 'test-bucket',
                    'Name': 'uploads/test-image.jpg'
                }
            },
            MaxLabels=10,
            MinConfidence=75
        )
        
        # Verify DynamoDB put_item was called
        self.assertTrue(mock_table.put_item.called)
        call_args = mock_table.put_item.call_args[1]
        item = call_args['Item']
        self.assertEqual(item['image_name'], 'test-image.jpg')
        self.assertIn('timestamp', item)
        self.assertEqual(len(item['labels']), 3)
        self.assertEqual(item['labels'][0]['name'], 'Dog')
        # Confidence should be Decimal
        from decimal import Decimal
        self.assertEqual(item['labels'][0]['confidence'], Decimal('98.50'))
    
    @patch('process_added_image.get_dynamodb_resource')
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_lambda_handler_with_url_encoded_key(self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb):
        """Test handling of URL-encoded file names."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        mock_rekognition.detect_labels.return_value = {
            'Labels': [{'Name': 'Test', 'Confidence': 90.0}]
        }
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Event with URL-encoded key (space as %20)
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': 'test-bucket'},
                        'object': {'key': 'uploads/my%20image.jpg'}
                    }
                }
            ]
        }
        
        context = Mock()
        response = process_added_image.lambda_handler(event, context)
        
        # Verify the response is successful
        self.assertEqual(response['statusCode'], 200)
        
        # Verify the decoded key was used in DynamoDB
        call_args = mock_table.put_item.call_args[1]
        item = call_args['Item']
        self.assertEqual(item['image_name'], 'my image.jpg')
    
    @patch('process_added_image.get_dynamodb_resource')
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_lambda_handler_multiple_records(self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb):
        """Test processing multiple images in one event."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        mock_rekognition.detect_labels.return_value = {
            'Labels': [{'Name': 'Test', 'Confidence': 90.0}]
        }
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Event with multiple records
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': 'test-bucket'},
                        'object': {'key': 'uploads/image1.jpg'}
                    }
                },
                {
                    's3': {
                        'bucket': {'name': 'test-bucket'},
                        'object': {'key': 'uploads/image2.png'}
                    }
                }
            ]
        }
        
        context = Mock()
        response = process_added_image.lambda_handler(event, context)
        
        # Verify both images were processed
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['processed_images'], 2)
        
        # Verify Rekognition was called twice
        self.assertEqual(mock_rekognition.detect_labels.call_count, 2)
        
        # Verify DynamoDB put_item was called twice
        self.assertEqual(mock_table.put_item.call_count, 2)
    
    @patch('process_added_image.get_dynamodb_resource')
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_rekognition_error(self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb):
        """Test handling of Rekognition errors."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock Rekognition to raise an exception
        mock_rekognition.detect_labels.side_effect = Exception('Rekognition service error')
        
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': 'test-bucket'},
                        'object': {'key': 'uploads/test-image.jpg'}
                    }
                }
            ]
        }
        
        context = Mock()
        
        # Should raise the exception
        with self.assertRaises(Exception) as cm:
            process_added_image.lambda_handler(event, context)
        
        self.assertIn('Rekognition service error', str(cm.exception))
        
        # Verify DynamoDB put_item was not called due to error
        mock_table.put_item.assert_not_called()
    
    @patch('process_added_image.get_dynamodb_resource')
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_dynamodb_put_error(self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb):
        """Test handling of DynamoDB put_item errors."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        mock_rekognition.detect_labels.return_value = {
            'Labels': [{'Name': 'Test', 'Confidence': 90.0}]
        }
        
        # Mock DynamoDB put_item to raise an exception
        mock_table.put_item.side_effect = Exception('DynamoDB access denied')
        
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': 'test-bucket'},
                        'object': {'key': 'uploads/test-image.jpg'}
                    }
                }
            ]
        }
        
        context = Mock()
        
        # Should raise the exception
        with self.assertRaises(Exception) as cm:
            process_added_image.lambda_handler(event, context)
        
        self.assertIn('DynamoDB access denied', str(cm.exception))
    
    @patch('process_added_image.get_dynamodb_resource')
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_empty_labels_response(self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb):
        """Test handling of empty labels from Rekognition."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock Rekognition response with no labels
        mock_rekognition.detect_labels.return_value = {'Labels': []}
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': 'test-bucket'},
                        'object': {'key': 'uploads/test-image.jpg'}
                    }
                }
            ]
        }
        
        context = Mock()
        response = process_added_image.lambda_handler(event, context)
        
        # Verify successful response even with no labels
        self.assertEqual(response['statusCode'], 200)
        
        # Verify empty labels were saved to DynamoDB
        call_args = mock_table.put_item.call_args[1]
        item = call_args['Item']
        self.assertEqual(len(item['labels']), 0)
    
    @patch('process_added_image.get_dynamodb_resource')
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_different_file_extensions(self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb):
        """Test processing different image file extensions."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        mock_rekognition.detect_labels.return_value = {
            'Labels': [{'Name': 'Test', 'Confidence': 90.0}]
        }
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Test different extensions
        test_files = ['test.jpg', 'test.jpeg', 'test.png']
        
        for filename in test_files:
            with self.subTest(filename=filename):
                event = {
                    'Records': [
                        {
                            's3': {
                                'bucket': {'name': 'test-bucket'},
                                'object': {'key': f'uploads/{filename}'}
                            }
                        }
                    ]
                }
                
                context = Mock()
                response = process_added_image.lambda_handler(event, context)
                
                self.assertEqual(response['statusCode'], 200)
                
                # Verify correct image name stored in DynamoDB
                call_args = mock_table.put_item.call_args[1]
                item = call_args['Item']
                self.assertEqual(item['image_name'], filename)
    
    def test_get_s3_client(self):
        """Test S3 client creation."""
        # Reset global client
        process_added_image.s3_client = None
        
        with patch('boto3.client') as mock_boto3:
            mock_client = Mock()
            mock_boto3.return_value = mock_client
            
            client = process_added_image.get_s3_client()
            
            self.assertEqual(client, mock_client)
            mock_boto3.assert_called_once_with('s3')
            
            # Test that subsequent calls return the same client
            client2 = process_added_image.get_s3_client()
            self.assertEqual(client, client2)
            # boto3.client should only be called once
            self.assertEqual(mock_boto3.call_count, 1)
    
    def test_get_rekognition_client(self):
        """Test Rekognition client creation."""
        # Reset global client
        process_added_image.rekognition_client = None
        
        with patch('boto3.client') as mock_boto3:
            mock_client = Mock()
            mock_boto3.return_value = mock_client
            
            client = process_added_image.get_rekognition_client()
            
            self.assertEqual(client, mock_client)
            mock_boto3.assert_called_once_with('rekognition')
            
            # Test that subsequent calls return the same client
            client2 = process_added_image.get_rekognition_client()
            self.assertEqual(client, client2)
            # boto3.client should only be called once
            self.assertEqual(mock_boto3.call_count, 1)
    
    def test_get_dynamodb_resource(self):
        """Test DynamoDB resource creation."""
        # Reset global resource
        process_added_image.dynamodb = None
        
        with patch('boto3.resource') as mock_boto3:
            mock_resource = Mock()
            mock_boto3.return_value = mock_resource
            
            resource = process_added_image.get_dynamodb_resource()
            
            self.assertEqual(resource, mock_resource)
            mock_boto3.assert_called_once_with('dynamodb')
            
            # Test that subsequent calls return the same resource
            resource2 = process_added_image.get_dynamodb_resource()
            self.assertEqual(resource, resource2)
            # boto3.resource should only be called once
            self.assertEqual(mock_boto3.call_count, 1)


    @patch('process_added_image.get_dynamodb_resource')
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_decimal_precision(self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb):
        """Test Decimal precision for confidence values."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        mock_rekognition.detect_labels.return_value = {
            'Labels': [{'Name': 'Test', 'Confidence': 99.123456789}]
        }
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'uploads/test.jpg'}
                }
            }]
        }
        
        process_added_image.lambda_handler(event, Mock())
        
        call_args = mock_table.put_item.call_args[1]
        from decimal import Decimal
        self.assertEqual(call_args['Item']['labels'][0]['confidence'], Decimal('99.123456789'))
    
    @patch('process_added_image.get_dynamodb_resource')
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_empty_event_records(self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb):
        """Test handling of empty Records array."""
        mock_get_s3.return_value = Mock()
        mock_get_rekognition.return_value = Mock()
        mock_get_dynamodb.return_value = Mock()
        
        event = {'Records': []}
        response = process_added_image.lambda_handler(event, Mock())
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['processed_images'], 0)
    
    @patch('process_added_image.get_dynamodb_resource')
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_nested_folder_structure(self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb):
        """Test handling of nested folder structures."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        mock_rekognition.detect_labels.return_value = {'Labels': []}
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'uploads/subfolder/image.jpg'}
                }
            }]
        }
        
        response = process_added_image.lambda_handler(event, Mock())
        
        self.assertEqual(response['statusCode'], 200)
        call_args = mock_table.put_item.call_args[1]
        self.assertEqual(call_args['Item']['image_name'], 'subfolder/image.jpg')


if __name__ == '__main__':
    unittest.main()