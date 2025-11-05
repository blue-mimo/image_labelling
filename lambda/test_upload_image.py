import unittest
from unittest.mock import patch, MagicMock
import json
import base64
import os
from upload_image import (
    lambda_handler,
    parse_multipart_data,
    get_file_name_and_data,
    upload_image_to_s3,
    decode_request_body,
    HTTPClientError,
)


class TestUploadImage(unittest.TestCase):

    @patch("upload_image.s3_client")
    def test_successful_upload(self, mock_s3):
        """Test successful image upload"""
        # Mock multipart form data
        boundary = "boundary123"
        file_content = b"fake-image-data"
        filename = "test.jpg"

        multipart_body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: image/jpeg\r\n"
                f"\r\n"
            ).encode()
            + file_content
            + f"\r\n--{boundary}--\r\n".encode()
        )

        event = {
            "httpMethod": "POST",
            "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
            "body": base64.b64encode(multipart_body).decode(),
            "isBase64Encoded": True,
        }

        mock_s3.put_object.return_value = {}

        response = lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["filename"], filename)
        self.assertEqual(body["s3_key"], f"uploads/{filename}")

        mock_s3.put_object.assert_called_once_with(
            Bucket="bluestone-image-labeling-a08324be2c5f",
            Key=f"uploads/{filename}",
            Body=file_content,
            ContentType="image/jpeg",
        )

    def test_options_request(self):
        """Test OPTIONS preflight request"""
        event = {"httpMethod": "OPTIONS"}

        response = lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 200)
        self.assertIn("Access-Control-Allow-Origin", response["headers"])

    def test_invalid_content_type(self):
        """Test invalid content type"""
        event = {
            "httpMethod": "POST",
            "headers": {"content-type": "application/json"},
            "body": "{}",
        }

        response = lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("Content-Type must be multipart/form-data", body["error"])

    def test_invalid_file_extension(self):
        """Test invalid file extension"""
        boundary = "boundary123"
        file_content = b"fake-file-data"
        filename = "test.txt"

        multipart_body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: text/plain\r\n"
                f"\r\n"
            ).encode()
            + file_content
            + f"\r\n--{boundary}--\r\n".encode()
        )

        event = {
            "httpMethod": "POST",
            "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
            "body": base64.b64encode(multipart_body).decode(),
            "isBase64Encoded": True,
        }

        response = lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("File type .txt not allowed", body["error"])

    def test_no_file_provided(self):
        """Test no file in request"""
        boundary = "boundary123"

        multipart_body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="text"\r\n'
            f"\r\n"
            f"some text\r\n"
            f"--{boundary}--\r\n"
        ).encode()

        event = {
            "httpMethod": "POST",
            "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
            "body": base64.b64encode(multipart_body).decode(),
            "isBase64Encoded": True,
        }

        response = lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["error"], "No file provided")

    def test_get_file_name_and_data_success(self):
        """Test successful file extraction"""
        boundary = "boundary123"
        file_content = b"test-content"
        filename = "test.png"

        multipart_body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: image/png\r\n"
                f"\r\n"
            ).encode()
            + file_content
            + f"\r\n--{boundary}--\r\n".encode()
        )

        event = {
            "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
            "body": base64.b64encode(multipart_body).decode(),
            "isBase64Encoded": True,
        }

        data, name, ext = get_file_name_and_data(event)

        self.assertEqual(data, file_content)
        self.assertEqual(name, filename)
        self.assertEqual(ext, ".png")

    def test_get_file_name_and_data_invalid_content_type(self):
        """Test invalid content type in get_file_name_and_data"""
        event = {"headers": {"content-type": "application/json"}, "body": "{}"}

        with self.assertRaises(HTTPClientError) as cm:
            get_file_name_and_data(event)

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("Content-Type must be multipart/form-data", cm.exception.message)

    def test_get_file_name_and_data_missing_headers(self):
        """Test missing headers"""
        event = {"body": ""}

        with self.assertRaises(HTTPClientError) as cm:
            get_file_name_and_data(event)

        self.assertEqual(cm.exception.status_code, 400)

    def test_get_file_name_and_data_no_file(self):
        """Test no file in multipart data"""
        boundary = "boundary123"
        multipart_body = f'--{boundary}\r\nContent-Disposition: form-data; name="text"\r\n\r\nsome text\r\n--{boundary}--\r\n'.encode()

        event = {
            "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
            "body": base64.b64encode(multipart_body).decode(),
            "isBase64Encoded": True,
        }

        with self.assertRaises(HTTPClientError) as cm:
            get_file_name_and_data(event)

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual(cm.exception.message, "No file provided")

    def test_get_file_name_and_data_invalid_extension(self):
        """Test invalid file extension"""
        boundary = "boundary123"
        multipart_body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
            f"\r\n"
            f"content\r\n--{boundary}--\r\n"
        ).encode()

        event = {
            "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
            "body": base64.b64encode(multipart_body).decode(),
            "isBase64Encoded": True,
        }

        with self.assertRaises(HTTPClientError) as cm:
            get_file_name_and_data(event)

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("File type .txt not allowed", cm.exception.message)

    def test_get_file_name_and_data_non_base64(self):
        """Test non-base64 encoded body"""
        boundary = "boundary123"
        multipart_body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="test.jpg"\r\n'
            f"\r\n"
            f"content\r\n--{boundary}--\r\n"
        )

        event = {
            "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
            "body": multipart_body,
            "isBase64Encoded": False,
        }

        data, name, ext = get_file_name_and_data(event)

        self.assertEqual(name, "test.jpg")
        self.assertEqual(ext, ".jpg")

    def test_parse_multipart_data_no_boundary(self):
        """Test parse_multipart_data with missing boundary"""
        result = parse_multipart_data(b"test", "multipart/form-data")
        self.assertEqual(result, (None, None))

    def test_parse_multipart_data_malformed(self):
        """Test parse_multipart_data with malformed data"""
        result = parse_multipart_data(
            b"malformed", "multipart/form-data; boundary=test"
        )
        self.assertEqual(result, (None, None))

    def test_parse_multipart_data_no_filename(self):
        """Test parse_multipart_data without filename"""
        boundary = "test"
        body = b'--test\r\nContent-Disposition: form-data; name="field"\r\n\r\nvalue\r\n--test--\r\n'
        result = parse_multipart_data(body, f"multipart/form-data; boundary={boundary}")
        self.assertEqual(result, (None, None))

    def test_lambda_handler_unexpected_error(self):
        """Test unexpected error in lambda_handler"""
        with patch("upload_image.get_file_name_and_data") as mock_get_file:
            mock_get_file.side_effect = ValueError("Unexpected error")

            event = {"httpMethod": "POST"}
            response = lambda_handler(event, {})

            self.assertEqual(response["statusCode"], 500)
            body = json.loads(response["body"])
            self.assertEqual(body["error"], "Internal server error")

    def test_all_file_extensions(self):
        """Test all supported file extensions"""
        extensions = [".jpg", ".jpeg", ".png", ".gif"]

        for ext in extensions:
            boundary = "boundary123"
            filename = f"test{ext}"
            multipart_body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"\r\n"
                f"content\r\n--{boundary}--\r\n"
            ).encode()

            event = {
                "headers": {
                    "content-type": f"multipart/form-data; boundary={boundary}"
                },
                "body": base64.b64encode(multipart_body).decode(),
                "isBase64Encoded": True,
            }

            data, name, file_ext = get_file_name_and_data(event)
            self.assertEqual(name, filename)
            self.assertEqual(file_ext, ext)

    @patch("upload_image.s3_client")
    def test_s3_error(self, mock_s3):
        """Test S3 upload error"""
        from botocore.exceptions import ClientError

        boundary = "boundary123"
        file_content = b"fake-image-data"
        filename = "test.jpg"

        multipart_body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: image/jpeg\r\n"
                f"\r\n"
            ).encode()
            + file_content
            + f"\r\n--{boundary}--\r\n".encode()
        )

        event = {
            "httpMethod": "POST",
            "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
            "body": base64.b64encode(multipart_body).decode(),
            "isBase64Encoded": True,
        }

        mock_s3.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )

        response = lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["error"], "Failed to upload to S3")

    @patch("upload_image.s3_client")
    def test_upload_image_to_s3_success(self, mock_s3):
        """Test successful S3 upload"""
        file_data = b"test-image-data"
        filename = "test.jpg"
        file_ext = ".jpg"

        mock_s3.put_object.return_value = {}

        s3_key = upload_image_to_s3(file_data, filename, file_ext)

        self.assertEqual(s3_key, "uploads/test.jpg")
        mock_s3.put_object.assert_called_once_with(
            Bucket="bluestone-image-labeling-a08324be2c5f",
            Key="uploads/test.jpg",
            Body=file_data,
            ContentType="image/jpeg",
        )

    @patch("upload_image.s3_client")
    def test_upload_image_to_s3_all_types(self, mock_s3):
        """Test S3 upload for all supported file types"""
        test_cases = [
            (".jpg", "image/jpeg"),
            (".jpeg", "image/jpeg"),
            (".png", "image/png"),
            (".gif", "image/gif"),
        ]

        mock_s3.put_object.return_value = {}

        for ext, content_type in test_cases:
            filename = f"test{ext}"
            s3_key = upload_image_to_s3(b"data", filename, ext)

            self.assertEqual(s3_key, f"uploads/{filename}")
            mock_s3.put_object.assert_called_with(
                Bucket="bluestone-image-labeling-a08324be2c5f",
                Key=f"uploads/{filename}",
                Body=b"data",
                ContentType=content_type,
            )

    def test_get_file_name_and_data_empty_body(self):
        """Test empty body handling"""
        event = {
            "headers": {"content-type": "multipart/form-data; boundary=test"},
            "body": "",
            "isBase64Encoded": False,
        }

        with self.assertRaises(HTTPClientError) as cm:
            get_file_name_and_data(event)

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual(cm.exception.message, "No file provided")

    def test_get_file_name_and_data_case_insensitive_extension(self):
        """Test case insensitive file extension handling"""
        boundary = "boundary123"
        filename = "TEST.JPG"
        multipart_body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"\r\n"
            f"content\r\n--{boundary}--\r\n"
        ).encode()

        event = {
            "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
            "body": base64.b64encode(multipart_body).decode(),
            "isBase64Encoded": True,
        }

        data, name, ext = get_file_name_and_data(event)

        self.assertEqual(name, filename)
        self.assertEqual(ext, ".jpg")  # Should be lowercase

    def test_parse_multipart_data_empty_filename(self):
        """Test multipart data with empty filename"""
        boundary = "test"
        body = b'--test\r\nContent-Disposition: form-data; name="file"; filename=""\r\n\r\ndata\r\n--test--\r\n'

        result = parse_multipart_data(body, f"multipart/form-data; boundary={boundary}")

        # Should return the empty filename
        self.assertEqual(result[1], "")

    def test_parse_multipart_data_multiple_parts(self):
        """Test multipart data with multiple parts, only one with file"""
        boundary = "test"
        body = (
            b"--test\r\n"
            b'Content-Disposition: form-data; name="text"\r\n'
            b"\r\n"
            b"some text\r\n"
            b"--test\r\n"
            b'Content-Disposition: form-data; name="file"; filename="test.jpg"\r\n'
            b"\r\n"
            b"file data\r\n"
            b"--test--\r\n"
        )

        result = parse_multipart_data(body, f"multipart/form-data; boundary={boundary}")

        self.assertEqual(result[0], b"file data")
        self.assertEqual(result[1], "test.jpg")

    @patch("upload_image.logger")
    def test_logging_coverage(self, mock_logger):
        """Test that debug logging is called"""
        boundary = "boundary123"
        multipart_body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="test.jpg"\r\n'
            f"\r\n"
            f"content\r\n--{boundary}--\r\n"
        ).encode()

        event = {
            "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
            "body": base64.b64encode(multipart_body).decode(),
            "isBase64Encoded": True,
        }

        get_file_name_and_data(event)

        # Verify debug logging was called
        mock_logger.debug.assert_called()

    def test_parse_multipart_data(self):
        """Test multipart data parsing"""
        boundary = "boundary123"
        file_content = b"test-file-content"
        filename = "test.png"

        multipart_body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: image/png\r\n"
                f"\r\n"
            ).encode()
            + file_content
            + f"\r\n--{boundary}--\r\n".encode()
        )

        content_type = f"multipart/form-data; boundary={boundary}"

        data, name = parse_multipart_data(multipart_body, content_type)

        self.assertEqual(data, file_content)
        self.assertEqual(name, filename)

    def test_parse_multipart_data_exception_handling(self):
        """Test exception handling in parse_multipart_data"""
        # Test with malformed content-type that will cause split to fail
        result = parse_multipart_data(b"test", "invalid-content-type")

        self.assertEqual(result, (None, None))

    def test_get_file_name_and_data_missing_content_type_header(self):
        """Test missing content-type header"""
        event = {"headers": {}, "body": ""}  # No content-type header

        with self.assertRaises(HTTPClientError) as cm:
            get_file_name_and_data(event)

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("Content-Type must be multipart/form-data", cm.exception.message)

    def test_parse_multipart_data_no_double_crlf(self):
        """Test multipart data without proper header/body separator"""
        boundary = "test"
        body = b'--test\r\nContent-Disposition: form-data; name="file"; filename="test.jpg"\r\ndata\r\n--test--\r\n'

        result = parse_multipart_data(body, f"multipart/form-data; boundary={boundary}")

        # Should handle missing double CRLF gracefully
        self.assertIsNotNone(result[0])  # Should still extract some data
        self.assertEqual(result[1], "test.jpg")

    def test_decode_request_body_base64(self):
        """Test decode_request_body with base64 encoded data"""
        test_data = b"test data"
        event = {
            "body": base64.b64encode(test_data).decode(),
            "isBase64Encoded": True
        }
        
        result = decode_request_body(event)
        
        self.assertEqual(result, test_data)

    def test_decode_request_body_non_base64(self):
        """Test decode_request_body with non-base64 data"""
        test_string = "test data"
        event = {
            "body": test_string,
            "isBase64Encoded": False
        }
        
        result = decode_request_body(event)
        
        self.assertEqual(result, test_string.encode("latin1"))

    def test_decode_request_body_empty(self):
        """Test decode_request_body with empty body"""
        event = {
            "body": "",
            "isBase64Encoded": False
        }
        
        result = decode_request_body(event)
        
        self.assertEqual(result, b"")


if __name__ == "__main__":
    unittest.main()
