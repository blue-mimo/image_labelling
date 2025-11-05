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
    
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_lambda_handler_success(self, mock_get_s3, mock_get_rekognition):
        """Test successful image labeling."""
        # Create mock clients
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        
        # Mock Rekognition response
        mock_rekognition.detect_labels.return_value = {
            'Labels': [
                {'Name': 'Dog', 'Confidence': 98.5},
                {'Name': 'Pet', 'Confidence': 97.3},
                {'Name': 'Animal', 'Confidence': 96.8}
            ]
        }
        
        # Mock S3 put_object
        mock_s3.put_object.return_value = {}
        
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
        
        # Verify S3 put_object was called
        self.assertTrue(mock_s3.put_object.called)
        call_args = mock_s3.put_object.call_args[1]
        self.assertEqual(call_args['Bucket'], 'test-bucket')
        self.assertEqual(call_args['Key'], 'labels/test-image.json')
        self.assertEqual(call_args['ContentType'], 'application/json')
        
        # Verify the labels content structure
        saved_data = json.loads(call_args['Body'])
        self.assertEqual(saved_data['image'], 'uploads/test-image.jpg')
        self.assertIn('timestamp', saved_data)
        self.assertEqual(len(saved_data['labels']), 3)
        self.assertEqual(saved_data['labels'][0]['name'], 'Dog')
        self.assertEqual(saved_data['labels'][0]['confidence'], 98.5)
    
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_lambda_handler_with_url_encoded_key(self, mock_get_s3, mock_get_rekognition):
        """Test handling of URL-encoded file names."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        
        mock_rekognition.detect_labels.return_value = {
            'Labels': [{'Name': 'Test', 'Confidence': 90.0}]
        }
        mock_s3.put_object.return_value = {}
        
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
        
        # Verify the decoded key was used
        call_args = mock_s3.put_object.call_args[1]
        saved_data = json.loads(call_args['Body'])
        self.assertEqual(saved_data['image'], 'uploads/my image.jpg')
    
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_lambda_handler_multiple_records(self, mock_get_s3, mock_get_rekognition):
        """Test processing multiple images in one event."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        
        mock_rekognition.detect_labels.return_value = {
            'Labels': [{'Name': 'Test', 'Confidence': 90.0}]
        }
        mock_s3.put_object.return_value = {}
        
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
        
        # Verify S3 put_object was called twice
        self.assertEqual(mock_s3.put_object.call_count, 2)
    
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_rekognition_error(self, mock_get_s3, mock_get_rekognition):
        """Test handling of Rekognition errors."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        
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
        
        # Verify S3 put_object was not called due to error
        mock_s3.put_object.assert_not_called()
    
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_s3_put_error(self, mock_get_s3, mock_get_rekognition):
        """Test handling of S3 put_object errors."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        
        mock_rekognition.detect_labels.return_value = {
            'Labels': [{'Name': 'Test', 'Confidence': 90.0}]
        }
        
        # Mock S3 put_object to raise an exception
        mock_s3.put_object.side_effect = Exception('S3 access denied')
        
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
        
        self.assertIn('S3 access denied', str(cm.exception))
    
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_empty_labels_response(self, mock_get_s3, mock_get_rekognition):
        """Test handling of empty labels from Rekognition."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        
        # Mock Rekognition response with no labels
        mock_rekognition.detect_labels.return_value = {'Labels': []}
        mock_s3.put_object.return_value = {}
        
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
        
        # Verify empty labels were saved
        call_args = mock_s3.put_object.call_args[1]
        saved_data = json.loads(call_args['Body'])
        self.assertEqual(len(saved_data['labels']), 0)
    
    @patch('process_added_image.get_rekognition_client')
    @patch('process_added_image.get_s3_client')
    def test_different_file_extensions(self, mock_get_s3, mock_get_rekognition):
        """Test processing different image file extensions."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        
        mock_rekognition.detect_labels.return_value = {
            'Labels': [{'Name': 'Test', 'Confidence': 90.0}]
        }
        mock_s3.put_object.return_value = {}
        
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
                
                # Verify correct label filename (extension changed to .json)
                expected_label_key = f'labels/{filename.rsplit(".", 1)[0]}.json'
                call_args = mock_s3.put_object.call_args[1]
                self.assertEqual(call_args['Key'], expected_label_key)
    
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


if __name__ == '__main__':
    unittest.main()