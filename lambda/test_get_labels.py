import json
import unittest
from unittest.mock import Mock, patch
import get_labels


class TestGetLabels(unittest.TestCase):
    
    @patch('get_labels.s3_client')
    def test_get_labels_success(self, mock_s3):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'image': 'uploads/test.jpg',
            'labels': [{'name': 'Dog', 'confidence': 98.5}]
        }).encode('utf-8')
        
        mock_s3.get_object.return_value = {'Body': mock_response}
        
        event = {'pathParameters': {'filename': 'test.jpg'}}
        response = get_labels.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['image'], 'uploads/test.jpg')
        self.assertEqual(len(body['labels']), 1)
        
        mock_s3.get_object.assert_called_once_with(
            Bucket='bluestone-image-labeling-a08324be2c5f',
            Key='labels/test.json'
        )
    
    @patch('get_labels.s3_client')
    def test_get_labels_not_found(self, mock_s3):
        mock_s3.get_object.side_effect = Exception('NoSuchKey')
        
        event = {'pathParameters': {'filename': 'nonexistent.jpg'}}
        response = get_labels.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertIn('error', body)
    
    def test_filename_extension_handling(self):
        event = {'pathParameters': {'filename': 'image.jpeg'}}
        
        with patch('get_labels.s3_client') as mock_s3:
            mock_response = Mock()
            mock_response.read.return_value = b'{"labels": []}'
            mock_s3.get_object.return_value = {'Body': mock_response}
            
            get_labels.lambda_handler(event, {})
            
            mock_s3.get_object.assert_called_once_with(
                Bucket='bluestone-image-labeling-a08324be2c5f',
                Key='labels/image.json'
            )


if __name__ == '__main__':
    unittest.main()