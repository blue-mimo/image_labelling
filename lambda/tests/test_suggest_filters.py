"""
Unit tests for suggest_filters Lambda function
"""
import unittest
from unittest.mock import Mock, patch
import json
from suggest_filters import lambda_handler


class TestSuggestFiltersLambdaHandler(unittest.TestCase):
    @patch("suggest_filters.table")
    def test_handler_success(self, mock_table):
        mock_table.get_item.return_value = {
            "Item": {"prefix": "do", "suggestions": ["dog", "door", "dolphin"]}
        }
        
        event = {"queryStringParameters": {"prefix": "do"}}
        result = lambda_handler(event, {})
        
        self.assertEqual(result["statusCode"], 200)
        self.assertIn("Access-Control-Allow-Origin", result["headers"])
        suggestions = json.loads(result["body"])
        self.assertEqual(len(suggestions), 3)
        self.assertIn("dog", suggestions)

    @patch("suggest_filters.table")
    def test_handler_no_results(self, mock_table):
        mock_table.get_item.return_value = {}
        
        event = {"queryStringParameters": {"prefix": "xyz"}}
        result = lambda_handler(event, {})
        
        self.assertEqual(result["statusCode"], 200)
        suggestions = json.loads(result["body"])
        self.assertEqual(suggestions, [])

    @patch("suggest_filters.table")
    def test_handler_missing_prefix(self, mock_table):
        event = {"queryStringParameters": {}}
        result = lambda_handler(event, {})
        
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("error", body)

    @patch("suggest_filters.table")
    def test_handler_no_query_params(self, mock_table):
        event = {}
        result = lambda_handler(event, {})
        
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("error", body)

    @patch("suggest_filters.table")
    def test_handler_url_encoded_prefix(self, mock_table):
        mock_table.get_item.return_value = {
            "Item": {"prefix": "test space", "suggestions": ["test space label"]}
        }
        
        event = {"queryStringParameters": {"prefix": "test+space"}}
        result = lambda_handler(event, {})
        
        self.assertEqual(result["statusCode"], 200)
        mock_table.get_item.assert_called_with(Key={"prefix": "test space"})

    @patch("suggest_filters.table")
    def test_handler_case_insensitive(self, mock_table):
        mock_table.get_item.return_value = {
            "Item": {"prefix": "dog", "suggestions": ["dog", "doghouse"]}
        }
        
        event = {"queryStringParameters": {"prefix": "DOG"}}
        result = lambda_handler(event, {})
        
        self.assertEqual(result["statusCode"], 200)
        mock_table.get_item.assert_called_with(Key={"prefix": "dog"})

    @patch("suggest_filters.table")
    def test_handler_dynamodb_error(self, mock_table):
        mock_table.get_item.side_effect = Exception("DynamoDB error")
        
        event = {"queryStringParameters": {"prefix": "do"}}
        result = lambda_handler(event, {})
        
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertIn("error", body)
        self.assertIn("details", body)

    @patch("suggest_filters.table")
    def test_handler_empty_suggestions(self, mock_table):
        mock_table.get_item.return_value = {
            "Item": {"prefix": "xyz", "suggestions": []}
        }
        
        event = {"queryStringParameters": {"prefix": "xyz"}}
        result = lambda_handler(event, {})
        
        self.assertEqual(result["statusCode"], 200)
        suggestions = json.loads(result["body"])
        self.assertEqual(suggestions, [])

    @patch("suggest_filters.table")
    def test_handler_cors_headers(self, mock_table):
        mock_table.get_item.return_value = {"Item": {"suggestions": ["dog"]}}
        
        event = {"queryStringParameters": {"prefix": "d"}}
        result = lambda_handler(event, {})
        
        self.assertIn("Access-Control-Allow-Origin", result["headers"])
        self.assertEqual(result["headers"]["Access-Control-Allow-Origin"], "*")
        self.assertIn("Content-Type", result["headers"])
        self.assertEqual(result["headers"]["Content-Type"], "application/json")

    @patch("suggest_filters.table")
    def test_handler_special_characters(self, mock_table):
        mock_table.get_item.return_value = {
            "Item": {"prefix": "c++", "suggestions": ["c++"]}
        }
        
        event = {"queryStringParameters": {"prefix": "c%2B%2B"}}
        result = lambda_handler(event, {})
        
        self.assertEqual(result["statusCode"], 200)

    @patch("suggest_filters.table")
    def test_handler_single_character_prefix(self, mock_table):
        mock_table.get_item.return_value = {
            "Item": {"prefix": "a", "suggestions": ["apple", "ant", "animal"]}
        }
        
        event = {"queryStringParameters": {"prefix": "a"}}
        result = lambda_handler(event, {})
        
        self.assertEqual(result["statusCode"], 200)
        suggestions = json.loads(result["body"])
        self.assertEqual(len(suggestions), 3)


if __name__ == "__main__":
    unittest.main()
