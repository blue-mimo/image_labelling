import json
import unittest
from unittest.mock import Mock, patch
import list_images


class TestListImages(unittest.TestCase):
    
    @patch('list_images.s3_client')
    def test_list_images_success(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'uploads/'},
                {'Key': 'uploads/image1.jpg'},
                {'Key': 'uploads/image2.png'},
                {'Key': 'uploads/image3.jpeg'},
                {'Key': 'uploads/document.pdf'}
            ]
        }
        
        response = list_images.lambda_handler({}, {})
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(len(body), 3)
        self.assertIn('image1.jpg', body)
        self.assertIn('image2.png', body)
        self.assertIn('image3.jpeg', body)
        self.assertNotIn('document.pdf', body)
    
    @patch('list_images.s3_client')
    def test_list_images_empty(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {}
        
        response = list_images.lambda_handler({}, {})
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body, [])
    
    @patch('list_images.s3_client')
    def test_list_images_error(self, mock_s3):
        mock_s3.list_objects_v2.side_effect = Exception('S3 error')
        
        response = list_images.lambda_handler({}, {})
        
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertIn('error', body)


if __name__ == '__main__':
    unittest.main()