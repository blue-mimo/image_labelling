import json
import unittest
from unittest.mock import Mock, patch
import base64
import get_image


class TestGetImage(unittest.TestCase):
    
    @patch('get_image.s3_client')
    def test_get_image_success_jpeg(self, mock_s3):
        # Mock JPEG image data (simplified)
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01test_image_data'
        mock_response = Mock()
        mock_response.read.return_value = jpeg_data
        mock_s3.get_object.return_value = {'Body': mock_response}
        
        event = {'pathParameters': {'filename': 'test.jpg'}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['headers']['Content-Type'], 'image/jpeg')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        self.assertTrue(response['isBase64Encoded'])
        
        # Verify base64 encoding
        decoded_data = base64.b64decode(response['body'])
        self.assertEqual(decoded_data, jpeg_data)
        
        mock_s3.get_object.assert_called_once_with(
            Bucket='bluestone-image-labeling-a08324be2c5f',
            Key='uploads/test.jpg'
        )
    
    @patch('get_image.s3_client')
    def test_get_image_success_png(self, mock_s3):
        # Mock PNG image data
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_png_data'
        mock_response = Mock()
        mock_response.read.return_value = png_data
        mock_s3.get_object.return_value = {'Body': mock_response}
        
        event = {'pathParameters': {'filename': 'test.png'}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['headers']['Content-Type'], 'image/png')
        self.assertTrue(response['isBase64Encoded'])
    
    @patch('get_image.s3_client')
    def test_get_image_not_found(self, mock_s3):
        mock_s3.get_object.side_effect = Exception('NoSuchKey')
        
        event = {'pathParameters': {'filename': 'nonexistent.jpg'}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 404)
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        body = json.loads(response['body'])
        self.assertIn('error', body)
    
    def test_missing_filename(self):
        event = {'pathParameters': {}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Filename not provided')
    
    def test_missing_path_parameters(self):
        event = {}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 400)
    
    @patch('get_image.s3_client')
    def test_empty_image_file(self, mock_s3):
        mock_response = Mock()
        mock_response.read.return_value = b''  # Empty file
        mock_s3.get_object.return_value = {'Body': mock_response}
        
        event = {'pathParameters': {'filename': 'empty.jpg'}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertIn('Image file is empty', body['error'])
    
    @patch('get_image.s3_client')
    def test_gif_image_detection(self, mock_s3):
        # Mock GIF87a image data
        gif_data = b'GIF87a\x01\x00\x01\x00test_gif_data'
        mock_response = Mock()
        mock_response.read.return_value = gif_data
        mock_s3.get_object.return_value = {'Body': mock_response}
        
        event = {'pathParameters': {'filename': 'test.gif'}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['headers']['Content-Type'], 'image/gif')
        
        # Test GIF89a as well
        gif89_data = b'GIF89a\x01\x00\x01\x00test_gif89_data'
        mock_response.read.return_value = gif89_data
        
        response = get_image.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 200)
    
    @patch('get_image.s3_client')
    def test_unknown_image_format(self, mock_s3):
        # Mock unknown format (should still work but log warning)
        unknown_data = b'\x00\x01\x02\x03unknown_format_data'
        mock_response = Mock()
        mock_response.read.return_value = unknown_data
        mock_s3.get_object.return_value = {'Body': mock_response}
        
        event = {'pathParameters': {'filename': 'test.jpg'}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['headers']['Content-Type'], 'image/jpeg')
    
    @patch('get_image.s3_client')
    def test_no_file_extension(self, mock_s3):
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01test_image_data'
        mock_response = Mock()
        mock_response.read.return_value = jpeg_data
        mock_s3.get_object.return_value = {'Body': mock_response}
        
        event = {'pathParameters': {'filename': 'noextension'}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertIn('No file extension found', body['error'])
    
    @patch('get_image.s3_client')
    def test_unrecognized_extension(self, mock_s3):
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01test_image_data'
        mock_response = Mock()
        mock_response.read.return_value = jpeg_data
        mock_s3.get_object.return_value = {'Body': mock_response}
        
        event = {'pathParameters': {'filename': 'test.xyz'}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertIn('Unrecognized file extension: .xyz', body['error'])
    
    @patch('get_image.s3_client')
    def test_s3_access_error(self, mock_s3):
        mock_s3.get_object.side_effect = Exception('Access Denied')
        
        event = {'pathParameters': {'filename': 'test.jpg'}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertIn('Access Denied', body['error'])
    
    def test_missing_filename_in_path_parameters(self):
        event = {'pathParameters': {}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Filename not provided')
    
    @patch('get_image.s3_client')
    def test_base64_encoding_validation(self, mock_s3):
        # Test that base64 encoding works correctly
        test_data = b'\xff\xd8\xff\xe0test_jpeg_data\xff\xd9'
        mock_response = Mock()
        mock_response.read.return_value = test_data
        mock_s3.get_object.return_value = {'Body': mock_response}
        
        event = {'pathParameters': {'filename': 'test.jpg'}}
        response = get_image.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        self.assertTrue(response['isBase64Encoded'])
        
        # Verify we can decode the base64 data back to original
        decoded_data = base64.b64decode(response['body'])
        self.assertEqual(decoded_data, test_data)
    
    @patch('get_image.s3_client')
    def test_all_supported_extensions(self, mock_s3):
        jpeg_data = b'\xff\xd8\xff\xe0test_data'
        mock_response = Mock()
        mock_response.read.return_value = jpeg_data
        mock_s3.get_object.return_value = {'Body': mock_response}
        
        # Test all supported extensions
        test_cases = [
            ('test.jpg', 'image/jpeg'),
            ('test.jpeg', 'image/jpeg'),
            ('test.png', 'image/png'),
            ('test.gif', 'image/gif'),
            ('TEST.JPG', 'image/jpeg'),  # Test case insensitive
        ]
        
        for filename, expected_type in test_cases:
            with self.subTest(filename=filename):
                event = {'pathParameters': {'filename': filename}}
                response = get_image.lambda_handler(event, {})
                
                self.assertEqual(response['statusCode'], 200)
                self.assertEqual(response['headers']['Content-Type'], expected_type)


if __name__ == '__main__':
    unittest.main()