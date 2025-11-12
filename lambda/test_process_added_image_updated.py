"""
Unit tests for the Lambda function with label counts functionality.
"""

import json
import unittest
from unittest.mock import Mock, patch
from decimal import Decimal

# Import the lambda function
import process_added_image


class TestLambdaFunction(unittest.TestCase):
    """Test cases for the image labeling Lambda function."""

    @patch("process_added_image.get_dynamodb_resource")
    @patch("process_added_image.get_rekognition_client")
    @patch("process_added_image.get_s3_client")
    def test_lambda_handler_success(
        self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb
    ):
        """Test successful image labeling with counts update."""
        # Create mock clients
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_counts_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.side_effect = lambda name: mock_counts_table if name == "label_counts" else mock_table

        # Mock Rekognition response
        mock_rekognition.detect_labels.return_value = {
            "Labels": [
                {"Name": "Dog", "Confidence": 98.5},
                {"Name": "Pet", "Confidence": 97.3},
            ]
        }

        # Mock DynamoDB responses
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_counts_table.update_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        # Create test event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "uploads/test-image.jpg"},
                    }
                }
            ]
        }

        # Call the Lambda handler
        context = Mock()
        response = process_added_image.lambda_handler(event, context)

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["message"], "Image labeling completed successfully")
        self.assertEqual(body["processed_images"], 1)

        # Verify DynamoDB put_item was called (2 label records)
        self.assertEqual(mock_table.put_item.call_count, 2)
        # Verify counts table update_item was called (2 times)
        self.assertEqual(mock_counts_table.update_item.call_count, 2)

        # Check first label record
        first_call = mock_table.put_item.call_args_list[0][1]
        item = first_call["Item"]
        self.assertEqual(item["image_name"], "test-image.jpg")
        self.assertEqual(item["label_name"], "dog")
        self.assertEqual(item["confidence"], Decimal("98.5"))

        # Check first count update
        first_count_call = mock_counts_table.update_item.call_args_list[0][1]
        self.assertEqual(first_count_call["Key"], {"label_name": "dog"})
        self.assertEqual(first_count_call["UpdateExpression"], "ADD #count :inc")
        self.assertEqual(first_count_call["ExpressionAttributeValues"], {":inc": 1})

    @patch("process_added_image.get_dynamodb_resource")
    @patch("process_added_image.get_rekognition_client") 
    @patch("process_added_image.get_s3_client")
    def test_counts_update_failure(
        self, mock_get_s3, mock_get_rekognition, mock_get_dynamodb
    ):
        """Test that label storage continues even if counts update fails."""
        mock_s3 = Mock()
        mock_rekognition = Mock()
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_counts_table = Mock()
        mock_get_s3.return_value = mock_s3
        mock_get_rekognition.return_value = mock_rekognition
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.side_effect = lambda name: mock_counts_table if name == "label_counts" else mock_table

        mock_rekognition.detect_labels.return_value = {
            "Labels": [{"Name": "Test", "Confidence": 90.0}]
        }
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        # Mock counts update to fail
        from botocore.exceptions import ClientError
        mock_counts_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "UpdateItem"
        )

        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "uploads/test.jpg"},
                    }
                }
            ]
        }

        # Should still succeed despite counts update failure
        with self.assertLogs('root', level='WARNING') as log:
            response = process_added_image.lambda_handler(event, Mock())
        
        self.assertEqual(response["statusCode"], 200)
        # Label should still be stored
        self.assertEqual(mock_table.put_item.call_count, 1)
        # Should have logged the warning
        self.assertTrue(any('Failed to update count' in message for message in log.output))


if __name__ == "__main__":
    unittest.main()