import json
import unittest
from unittest.mock import Mock, patch
import list_images


class TestListImages(unittest.TestCase):

    @patch("list_images.s3_client")
    def test_list_images_success(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "uploads/"},
                {"Key": "uploads/image1.jpg"},
                {"Key": "uploads/image2.png"},
                {"Key": "uploads/image3.jpeg"},
                {"Key": "uploads/document.pdf"},
            ]
        }

        event = {"queryStringParameters": {"page": "0", "limit": "10"}}
        response = list_images.lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(len(body["images"]), 3)
        self.assertIn("image1.jpg", body["images"])
        self.assertEqual(body["pagination"]["total"], 3)
        self.assertEqual(body["pagination"]["totalPages"], 1)

    @patch("list_images.s3_client")
    def test_list_images_empty(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {}

        event = {"queryStringParameters": None}
        response = list_images.lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["images"], [])
        self.assertEqual(body["pagination"]["total"], 0)

    @patch("list_images.s3_client")
    def test_pagination(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": f"uploads/image{i}.jpg"} for i in range(1, 26)]
        }

        event = {"queryStringParameters": {"page": "1", "limit": "10"}}
        response = list_images.lambda_handler(event, {})

        body = json.loads(response["body"])
        self.assertEqual(len(body["images"]), 10)
        self.assertEqual(body["pagination"]["page"], 1)
        self.assertEqual(body["pagination"]["total"], 25)
        self.assertEqual(body["pagination"]["totalPages"], 3)

    @patch("list_images.table")
    @patch("list_images.s3_client")
    def test_filtering(self, mock_s3, mock_table):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "uploads/dog.jpg"}, {"Key": "uploads/cat.jpg"}]
        }

        # Mock DynamoDB query response
        mock_table.query.return_value = {
            "Items": [
                {"image_name": "dog.jpg", "label_name": "dog", "confidence": 95.0}
            ]
        }

        event = {"queryStringParameters": {"filters": "dog"}}
        response = list_images.lambda_handler(event, {})

        body = json.loads(response["body"])
        self.assertEqual(len(body["images"]), 1)
        self.assertIn("dog.jpg", body["images"])

        # Verify DynamoDB query was called
        mock_table.query.assert_called_once()

    @patch("list_images.s3_client")
    def test_default_parameters(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "uploads/test.jpg"}]
        }

        response = list_images.lambda_handler({}, {})

        body = json.loads(response["body"])
        self.assertEqual(body["pagination"]["page"], 0)
        self.assertEqual(body["pagination"]["limit"], 10)

    @patch("list_images.s3_client")
    def test_empty_filters(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "uploads/test.jpg"}]
        }

        event = {"queryStringParameters": {"filters": ""}}
        response = list_images.lambda_handler(event, {})

        body = json.loads(response["body"])
        self.assertEqual(len(body["images"]), 1)

    @patch("list_images.table")
    @patch("list_images.s3_client")
    def test_multiple_filters(self, mock_s3, mock_table):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "uploads/animal.jpg"}]
        }

        # Mock DynamoDB query responses for multiple filters
        def mock_query(**kwargs):
            label = kwargs["ExpressionAttributeValues"][":label"]
            if label == "dog":
                return {"Items": [{"image_name": "animal.jpg", "label_name": "dog"}]}
            elif label == "cat":
                return {"Items": []}
            return {"Items": []}

        mock_table.query.side_effect = mock_query

        event = {"queryStringParameters": {"filters": "dog,cat"}}
        response = list_images.lambda_handler(event, {})

        body = json.loads(response["body"])
        self.assertEqual(len(body["images"]), 1)
        self.assertEqual(mock_table.query.call_count, 2)

    @patch("list_images.table")
    @patch("list_images.s3_client")
    def test_filter_no_match(self, mock_s3, mock_table):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "uploads/test.jpg"}]
        }

        # Mock DynamoDB query with no results
        mock_table.query.return_value = {"Items": []}

        event = {"queryStringParameters": {"filters": "dog"}}
        response = list_images.lambda_handler(event, {})

        body = json.loads(response["body"])
        self.assertEqual(len(body["images"]), 0)

    @patch("list_images.table")
    @patch("list_images.s3_client")
    def test_filter_label_error(self, mock_s3, mock_table):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "uploads/test.jpg"}]
        }

        # Mock DynamoDB query error
        mock_table.query.side_effect = Exception("DynamoDB error")

        event = {"queryStringParameters": {"filters": "dog"}}
        response = list_images.lambda_handler(event, {})

        body = json.loads(response["body"])
        self.assertEqual(len(body["images"]), 0)

    @patch("list_images.s3_client")
    def test_last_page(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": f"uploads/image{i}.jpg"} for i in range(1, 8)]
        }

        event = {"queryStringParameters": {"page": "1", "limit": "5"}}
        response = list_images.lambda_handler(event, {})

        body = json.loads(response["body"])
        self.assertEqual(len(body["images"]), 2)
        self.assertEqual(body["pagination"]["totalPages"], 2)

    @patch("list_images.s3_client")
    def test_page_beyond_range(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "uploads/test.jpg"}]
        }

        event = {"queryStringParameters": {"page": "5", "limit": "10"}}
        response = list_images.lambda_handler(event, {})

        body = json.loads(response["body"])
        self.assertEqual(len(body["images"]), 0)
        self.assertEqual(body["pagination"]["page"], 5)

    @patch("list_images.s3_client")
    def test_file_extensions(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "uploads/image.JPG"},
                {"Key": "uploads/image.JPEG"},
                {"Key": "uploads/image.PNG"},
                {"Key": "uploads/doc.txt"},
            ]
        }

        response = list_images.lambda_handler({}, {})

        body = json.loads(response["body"])
        self.assertEqual(len(body["images"]), 3)

    @patch("list_images.s3_client")
    def test_list_images_error(self, mock_s3):
        mock_s3.list_objects_v2.side_effect = Exception("S3 error")

        response = list_images.lambda_handler({}, {})

        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
