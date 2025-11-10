import json
import unittest
from unittest.mock import Mock, patch
from decimal import Decimal
import get_labels


class TestGetLabels(unittest.TestCase):

    @patch("get_labels.table")
    def test_get_labels_success(self, mock_table):
        mock_table.get_item.return_value = {
            'Item': {
                'image_name': 'test.jpg',
                'timestamp': '2024-01-01T00:00:00Z',
                'labels': [{'name': 'Dog', 'confidence': Decimal('98.5')}]
            }
        }

        event = {"pathParameters": {"filename": "test.jpg"}}
        response = get_labels.lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Content-Type"], "application/json")
        self.assertEqual(response["headers"]["Access-Control-Allow-Origin"], "*")
        body = json.loads(response["body"])
        self.assertEqual(body["image"], "uploads/test.jpg")
        self.assertEqual(len(body["labels"]), 1)
        self.assertEqual(body["labels"][0]["confidence"], 98.5)  # Should be converted to float

        mock_table.get_item.assert_called_once_with(
            Key={'image_name': 'test.jpg'}
        )

    @patch("get_labels.table")
    def test_get_labels_not_found(self, mock_table):
        mock_table.get_item.return_value = {}  # No 'Item' key means not found

        event = {"pathParameters": {"filename": "nonexistent.jpg"}}
        response = get_labels.lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertIn("error", body)

    @patch("get_labels.table")
    def test_filename_extension_handling(self, mock_table):
        mock_table.get_item.return_value = {
            'Item': {
                'image_name': 'image.jpeg',
                'timestamp': '2024-01-01T00:00:00Z',
                'labels': []
            }
        }

        event = {"pathParameters": {"filename": "image.jpeg"}}
        response = get_labels.lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 200)
        mock_table.get_item.assert_called_once_with(
            Key={'image_name': 'image.jpeg'}
        )

    def test_missing_path_parameters(self):
        event = {}
        response = get_labels.lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["headers"]["Content-Type"], "application/json")
        body = json.loads(response["body"])
        self.assertEqual(body["error"], "Filename not provided")
    
    @patch("get_labels.table")
    def test_dynamodb_error(self, mock_table):
        mock_table.get_item.side_effect = Exception('DynamoDB error')
        
        event = {"pathParameters": {"filename": "test.jpg"}}
        response = get_labels.lambda_handler(event, {})
        
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertIn("error", body)
        self.assertEqual(body["error"], "DynamoDB error")
    
    @patch("get_labels.table")
    def test_empty_labels_array(self, mock_table):
        mock_table.get_item.return_value = {
            'Item': {
                'image_name': 'test.jpg',
                'timestamp': '2024-01-01T00:00:00Z',
                'labels': []
            }
        }
        
        event = {"pathParameters": {"filename": "test.jpg"}}
        response = get_labels.lambda_handler(event, {})
        
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(len(body["labels"]), 0)
    
    @patch("get_labels.table")
    def test_multiple_labels_decimal_conversion(self, mock_table):
        mock_table.get_item.return_value = {
            'Item': {
                'image_name': 'test.jpg',
                'timestamp': '2024-01-01T00:00:00Z',
                'labels': [
                    {'name': 'Dog', 'confidence': Decimal('98.123')},
                    {'name': 'Pet', 'confidence': Decimal('95.456')}
                ]
            }
        }
        
        event = {"pathParameters": {"filename": "test.jpg"}}
        response = get_labels.lambda_handler(event, {})
        
        body = json.loads(response["body"])
        self.assertEqual(body["labels"][0]["confidence"], 98.123)
        self.assertEqual(body["labels"][1]["confidence"], 95.456)
    
    def test_missing_filename_in_path_parameters(self):
        event = {"pathParameters": {}}
        response = get_labels.lambda_handler(event, {})
        
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["error"], "Filename not provided")


if __name__ == "__main__":
    unittest.main()
