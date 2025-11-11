"""
Unit tests for the delete_image Lambda function with label counts functionality.
"""

import json
import unittest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
import os

# Import the lambda function
import delete_image


class TestDeleteImageUpdated(unittest.TestCase):
    """Test cases for the delete image Lambda function with counts."""

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
    def test_lambda_handler_success_with_counts(self, mock_resource, mock_client, mock_delete_labels, mock_delete_s3):
        """Test successful image deletion with counts update."""
        # Mock AWS clients
        mock_table = Mock()
        mock_counts_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.side_effect = lambda name: mock_counts_table if name == 'label_counts' else mock_table
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

        # Verify helper functions were called with both tables
        mock_delete_labels.assert_called_once_with(mock_table, mock_counts_table, 'test-image.jpg')
        mock_delete_s3.assert_called_once_with(mock_s3_client, 'test-bucket', 'test-image.jpg')

    def test_delete_image_labels_with_counts(self):
        """Test successful label deletion with counts decrement."""
        mock_table = Mock()
        mock_counts_table = Mock()
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

        result = delete_image.delete_image_labels(mock_table, mock_counts_table, 'test.jpg')

        self.assertEqual(result, 2)
        mock_table.query.assert_called_once()
        self.assertEqual(mock_batch.delete_item.call_count, 2)
        # Verify counts were decremented
        self.assertEqual(mock_counts_table.update_item.call_count, 2)
        
        # Check first count decrement call
        first_call = mock_counts_table.update_item.call_args_list[0][1]
        self.assertEqual(first_call['Key'], {'label_name': 'dog'})
        self.assertEqual(first_call['UpdateExpression'], 'ADD #count :dec')
        self.assertEqual(first_call['ExpressionAttributeValues'], {':dec': -1})

    def test_delete_image_labels_counts_error(self):
        """Test that label deletion continues even if counts update fails."""
        mock_table = Mock()
        mock_counts_table = Mock()
        mock_table.query.return_value = {
            'Items': [{'image_name': 'test.jpg', 'label_name': 'dog'}]
        }
        
        mock_batch = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager
        
        # Mock counts update to fail
        mock_counts_table.update_item.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'UpdateItem'
        )

        # Should still succeed and return count
        result = delete_image.delete_image_labels(mock_table, mock_counts_table, 'test.jpg')
        
        self.assertEqual(result, 1)
        # Label should still be deleted
        self.assertEqual(mock_batch.delete_item.call_count, 1)

    def test_delete_image_labels_no_items(self):
        """Test delete_image_labels when no labels exist."""
        mock_table = Mock()
        mock_counts_table = Mock()
        mock_table.query.return_value = {'Items': []}
        
        result = delete_image.delete_image_labels(mock_table, mock_counts_table, 'test.jpg')
        
        self.assertEqual(result, 0)
        mock_table.batch_writer.assert_not_called()
        mock_counts_table.update_item.assert_not_called()

    @patch('boto3.client')
    def test_delete_image_from_s3_success(self, mock_client):
        """Test successful S3 deletion."""
        mock_s3_client = Mock()
        mock_client.return_value = mock_s3_client
        
        delete_image.delete_image_from_s3(mock_s3_client, 'test-bucket', 'test.jpg')
        
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket='test-bucket', Key='uploads/test.jpg'
        )

    @patch('boto3.client')
    def test_delete_image_from_s3_no_such_key(self, mock_client):
        """Test S3 deletion when file doesn't exist."""
        mock_s3_client = Mock()
        mock_client.return_value = mock_s3_client
        mock_s3_client.delete_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'DeleteObject'
        )
        
        # Should not raise exception
        delete_image.delete_image_from_s3(mock_s3_client, 'test-bucket', 'test.jpg')
        
        mock_s3_client.delete_object.assert_called_once()

    @patch('boto3.client')
    def test_delete_image_from_s3_other_error(self, mock_client):
        """Test S3 deletion with other errors."""
        mock_s3_client = Mock()
        mock_client.return_value = mock_s3_client
        mock_s3_client.delete_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'DeleteObject'
        )
        
        with self.assertRaises(ClientError):
            delete_image.delete_image_from_s3(mock_s3_client, 'test-bucket', 'test.jpg')

    def test_lambda_handler_missing_filename(self):
        """Test lambda handler with missing filename."""
        event = {'pathParameters': {}}
        context = Mock()
        
        response = delete_image.lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Filename is required')

    def test_lambda_handler_no_path_params(self):
        """Test lambda handler with no path parameters."""
        event = {}
        context = Mock()
        
        response = delete_image.lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Filename is required')

    def test_lambda_handler_missing_bucket_env(self):
        """Test lambda handler with missing BUCKET_NAME environment variable."""
        if 'BUCKET_NAME' in os.environ:
            del os.environ['BUCKET_NAME']
        
        event = {'pathParameters': {'filename': 'test.jpg'}}
        context = Mock()
        
        response = delete_image.lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Server configuration error')

    @patch('boto3.resource')
    def test_lambda_handler_aws_init_error(self, mock_resource):
        """Test lambda handler with AWS client initialization error."""
        mock_resource.side_effect = Exception('AWS init failed')
        
        event = {'pathParameters': {'filename': 'test.jpg'}}
        context = Mock()
        
        response = delete_image.lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Failed to initialize AWS services')

    @patch('delete_image.delete_image_from_s3')
    @patch('delete_image.delete_image_labels')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_lambda_handler_dynamodb_error(self, mock_resource, mock_client, mock_delete_labels, mock_delete_s3):
        """Test lambda handler with DynamoDB error."""
        mock_table = Mock()
        mock_counts_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.side_effect = lambda name: mock_counts_table if name == 'label_counts' else mock_table
        mock_resource.return_value = mock_dynamodb
        mock_s3_client = Mock()
        mock_client.return_value = mock_s3_client
        
        mock_delete_labels.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}}, 'Query'
        )
        
        event = {'pathParameters': {'filename': 'test.jpg'}}
        context = Mock()
        
        response = delete_image.lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Failed to delete labels: ResourceNotFoundException')

    @patch('delete_image.delete_image_from_s3')
    @patch('delete_image.delete_image_labels')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_lambda_handler_s3_error(self, mock_resource, mock_client, mock_delete_labels, mock_delete_s3):
        """Test lambda handler with S3 error."""
        mock_table = Mock()
        mock_counts_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.side_effect = lambda name: mock_counts_table if name == 'label_counts' else mock_table
        mock_resource.return_value = mock_dynamodb
        mock_s3_client = Mock()
        mock_client.return_value = mock_s3_client
        
        mock_delete_labels.return_value = 2
        mock_delete_s3.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'DeleteObject'
        )
        
        event = {'pathParameters': {'filename': 'test.jpg'}}
        context = Mock()
        
        response = delete_image.lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Failed to delete image from S3: AccessDenied')

    def test_lambda_handler_unexpected_error(self):
        """Test lambda handler with unexpected error."""
        # Trigger error in event processing itself
        event = None  # This will cause an AttributeError
        context = Mock()
        
        response = delete_image.lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Internal server error')


if __name__ == '__main__':
    unittest.main()