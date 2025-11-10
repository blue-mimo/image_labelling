"""
Unit tests for the delete_image Lambda function.
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
import os

# Import the lambda function
import delete_image


class TestDeleteImage(unittest.TestCase):
    """Test cases for the delete image Lambda function."""

    def setUp(self):
        """Set up test environment."""
        os.environ['BUCKET_NAME'] = 'test-bucket'

    def tearDown(self):
        """Clean up test environment."""
        if 'BUCKET_NAME' in os.environ:
            del os.environ['BUCKET_NAME']

    @patch('delete_image.delete_image_from_s3')
    @patch('delete_image.delete_image_labels')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_lambda_handler_success(self, mock_resource, mock_client, mock_delete_labels, mock_delete_s3):
        """Test successful image deletion."""
        # Mock AWS clients
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        mock_s3_client = Mock()
        mock_client.return_value = mock_s3_client

        # Mock helper functions
        mock_delete_labels.return_value = 3
        mock_delete_s3.return_value = None

        event = {
            'pathParameters': {'filename': 'test-image.jpg'}
        }
        context = Mock()

        response = delete_image.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        self.assertIn('headers', response)
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'Image test-image.jpg deleted successfully')
        self.assertEqual(body['deleted_labels'], 3)

        # Verify helper functions were called
        mock_delete_labels.assert_called_once_with(mock_table, 'test-image.jpg')
        mock_delete_s3.assert_called_once_with(mock_s3_client, 'test-bucket', 'test-image.jpg')

    def test_lambda_handler_missing_filename(self):
        """Test error when filename is missing."""
        event = {'pathParameters': {}}
        context = Mock()

        response = delete_image.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        self.assertIn('headers', response)
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Filename is required')

    def test_lambda_handler_missing_bucket_env(self):
        """Test error when BUCKET_NAME environment variable is missing."""
        del os.environ['BUCKET_NAME']
        
        event = {'pathParameters': {'filename': 'test.jpg'}}
        context = Mock()

        response = delete_image.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('headers', response)
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Server configuration error')

    @patch('delete_image.delete_image_labels')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_lambda_handler_dynamodb_error(self, mock_resource, mock_client, mock_delete_labels):
        """Test DynamoDB error handling."""
        # Mock AWS clients
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        mock_client.return_value = Mock()

        # Mock DynamoDB error
        error = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'Query'
        )
        mock_delete_labels.side_effect = error

        event = {'pathParameters': {'filename': 'test.jpg'}}
        context = Mock()

        response = delete_image.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('headers', response)
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Failed to delete labels: AccessDenied')

    def test_delete_image_labels_success(self):
        """Test successful label deletion."""
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': [
                {'image_name': 'test.jpg', 'label_name': 'dog'},
                {'image_name': 'test.jpg', 'label_name': 'animal'}
            ]
        }
        
        mock_batch = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager

        result = delete_image.delete_image_labels(mock_table, 'test.jpg')

        self.assertEqual(result, 2)
        mock_table.query.assert_called_once()
        self.assertEqual(mock_batch.delete_item.call_count, 2)

    def test_delete_image_labels_no_labels(self):
        """Test label deletion when no labels exist."""
        mock_table = Mock()
        mock_table.query.return_value = {'Items': []}

        result = delete_image.delete_image_labels(mock_table, 'test.jpg')

        self.assertEqual(result, 0)
        mock_table.batch_writer.assert_not_called()

    def test_delete_image_from_s3_success(self):
        """Test successful S3 deletion."""
        mock_s3_client = Mock()
        
        delete_image.delete_image_from_s3(mock_s3_client, 'test-bucket', 'test.jpg')
        
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket='test-bucket', 
            Key='uploads/test.jpg'
        )

    def test_delete_image_from_s3_not_found(self):
        """Test S3 deletion when file doesn't exist."""
        mock_s3_client = Mock()
        error = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Key not found'}},
            'DeleteObject'
        )
        mock_s3_client.delete_object.side_effect = error

        # Should not raise exception for NoSuchKey
        delete_image.delete_image_from_s3(mock_s3_client, 'test-bucket', 'test.jpg')
        
        mock_s3_client.delete_object.assert_called_once()

    def test_delete_image_from_s3_other_error(self):
        """Test S3 deletion with other errors."""
        mock_s3_client = Mock()
        error = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'DeleteObject'
        )
        mock_s3_client.delete_object.side_effect = error

        with self.assertRaises(ClientError):
            delete_image.delete_image_from_s3(mock_s3_client, 'test-bucket', 'test.jpg')

    @patch('delete_image.delete_image_from_s3')
    @patch('delete_image.delete_image_labels')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_lambda_handler_s3_error(self, mock_resource, mock_client, mock_delete_labels, mock_delete_s3):
        """Test S3 error handling."""
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        mock_client.return_value = Mock()

        mock_delete_labels.return_value = 2
        error = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'DeleteObject'
        )
        mock_delete_s3.side_effect = error

        event = {'pathParameters': {'filename': 'test.jpg'}}
        context = Mock()

        response = delete_image.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('headers', response)
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Failed to delete image from S3: AccessDenied')

    @patch('boto3.resource')
    def test_lambda_handler_aws_init_error(self, mock_resource):
        """Test AWS client initialization error."""
        mock_resource.side_effect = Exception('AWS connection failed')

        event = {'pathParameters': {'filename': 'test.jpg'}}
        context = Mock()

        response = delete_image.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('headers', response)
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Failed to initialize AWS services')

    @patch('delete_image.delete_image_from_s3')
    @patch('delete_image.delete_image_labels')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_lambda_handler_unexpected_error(self, mock_resource, mock_client, mock_delete_labels, mock_delete_s3):
        """Test unexpected error handling."""
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        mock_client.return_value = Mock()

        mock_delete_labels.side_effect = Exception('Unexpected error')

        event = {'pathParameters': {'filename': 'test.jpg'}}
        context = Mock()

        response = delete_image.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('headers', response)
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Internal server error')

    def test_delete_image_labels_dynamodb_error(self):
        """Test DynamoDB error in delete_image_labels."""
        mock_table = Mock()
        error = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}},
            'Query'
        )
        mock_table.query.side_effect = error

        with self.assertRaises(ClientError):
            delete_image.delete_image_labels(mock_table, 'test.jpg')

    def test_delete_image_labels_batch_error(self):
        """Test batch writer error in delete_image_labels."""
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': [{'image_name': 'test.jpg', 'label_name': 'dog'}]
        }
        
        mock_batch = Mock()
        mock_batch.delete_item.side_effect = Exception('Batch error')
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager

        with self.assertRaises(Exception):
            delete_image.delete_image_labels(mock_table, 'test.jpg')

    def test_lambda_handler_none_path_parameters(self):
        """Test error when pathParameters is None."""
        event = {'pathParameters': None}
        context = Mock()

        response = delete_image.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        self.assertIn('headers', response)
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Filename is required')

    def test_lambda_handler_empty_filename(self):
        """Test error when filename is empty string."""
        event = {'pathParameters': {'filename': ''}}
        context = Mock()

        response = delete_image.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        self.assertIn('headers', response)
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Filename is required')


if __name__ == '__main__':
    unittest.main()