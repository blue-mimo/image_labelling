"""
Unit tests for update_prefix_suggestions Lambda function
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from update_prefix_suggestions import (
    CountedLabel,
    PrefixSuggestions,
    _query_labels_by_letter,
    _inject_prefixes_into_shorter_dict,
    _compute_suggestions,
    _batch_update_suggestions,
    _batch_delete_obsolete_prefixes,
    lambda_handler,
)


class TestCountedLabel(unittest.TestCase):
    def test_init(self):
        label = CountedLabel("dog", 10)
        self.assertEqual(label.label_name, "dog")
        self.assertEqual(label.count, 10)

    def test_comparison_lt(self):
        label1 = CountedLabel("dog", 5)
        label2 = CountedLabel("cat", 10)
        self.assertTrue(label1 < label2)
        self.assertFalse(label2 < label1)

    def test_comparison_eq(self):
        label1 = CountedLabel("dog", 10)
        label2 = CountedLabel("dog", 10)
        label3 = CountedLabel("cat", 10)
        self.assertTrue(label1 == label2)
        self.assertFalse(label1 == label3)


class TestPrefixSuggestions(unittest.TestCase):
    def test_init(self):
        ps = PrefixSuggestions()
        self.assertEqual(ps.counted_labels, [])
        self.assertEqual(ps.overall_count, 0)

    def test_insert_valid(self):
        ps = PrefixSuggestions()
        ps.insert("dog", 10)
        self.assertEqual(len(ps.counted_labels), 1)
        self.assertEqual(ps.overall_count, 10)

    def test_insert_invalid_label_name(self):
        ps = PrefixSuggestions()
        with self.assertRaises(ValueError):
            ps.insert("", 10)
        with self.assertRaises(ValueError):
            ps.insert(None, 10)

    def test_insert_invalid_count(self):
        ps = PrefixSuggestions()
        with self.assertRaises(ValueError):
            ps.insert("dog", -1)
        with self.assertRaises(ValueError):
            ps.insert("dog", "invalid")

    def test_insert_max_suggestions(self):
        ps = PrefixSuggestions()
        for i in range(15):
            ps.insert(f"label{i}", i)
        self.assertEqual(len(ps.counted_labels), 10)

    def test_deepcopy(self):
        import copy
        ps = PrefixSuggestions()
        ps.insert("dog", 10)
        ps_copy = copy.deepcopy(ps)
        self.assertEqual(ps_copy.overall_count, 10)
        self.assertEqual(len(ps_copy.counted_labels), 1)


class TestQueryLabelsByLetter(unittest.TestCase):
    def test_query_success(self):
        mock_table = Mock()
        mock_table.scan.return_value = {
            "Items": [{"label_name": "dog", "count": 10}]
        }
        result = _query_labels_by_letter(mock_table, "d")
        self.assertEqual(len(result["Items"]), 1)
        self.assertEqual(result["Items"][0]["label_name"], "dog")

    def test_query_with_pagination(self):
        mock_table = Mock()
        mock_table.scan.side_effect = [
            {"Items": [{"label_name": "dog", "count": 10}], "LastEvaluatedKey": "key"},
            {"Items": [{"label_name": "door", "count": 5}]},
        ]
        result = _query_labels_by_letter(mock_table, "d")
        self.assertEqual(len(result["Items"]), 2)

    @patch('update_prefix_suggestions.logger')
    def test_query_resource_not_found(self, mock_logger):
        mock_table = Mock()
        not_found_exception = type('ResourceNotFoundException', (Exception,), {})
        mock_table.meta.client.exceptions.ResourceNotFoundException = not_found_exception
        mock_table.meta.client.exceptions.ProvisionedThroughputExceededException = Exception
        mock_table.meta.client.exceptions.RequestLimitExceeded = Exception
        mock_table.scan.side_effect = not_found_exception("Not found")
        result = _query_labels_by_letter(mock_table, "d")
        self.assertIsNone(result)

    @patch('update_prefix_suggestions.logger')
    def test_query_throttling(self, mock_logger):
        mock_table = Mock()
        throttle_exception = type('ProvisionedThroughputExceededException', (Exception,), {})
        mock_table.meta.client.exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        mock_table.meta.client.exceptions.ProvisionedThroughputExceededException = throttle_exception
        mock_table.meta.client.exceptions.RequestLimitExceeded = type('RequestLimitExceeded', (Exception,), {})
        mock_table.scan.side_effect = throttle_exception("Throttled")
        result = _query_labels_by_letter(mock_table, "d")
        self.assertIsNone(result)


class TestInjectPrefixesIntoShorterDict(unittest.TestCase):
    def test_inject_new_prefix(self):
        current = {"dog": PrefixSuggestions()}
        current["dog"].insert("dog", 10)
        shorter = {}
        _inject_prefixes_into_shorter_dict(current, shorter)
        self.assertIn("do", shorter)

    def test_inject_existing_prefix(self):
        current = {"dog": PrefixSuggestions()}
        current["dog"].insert("dog", 10)
        shorter = {"do": PrefixSuggestions()}
        shorter["do"].insert("door", 5)
        _inject_prefixes_into_shorter_dict(current, shorter)
        self.assertEqual(len(shorter["do"].counted_labels), 2)

    def test_inject_empty_prefix(self):
        current = {"": PrefixSuggestions()}
        shorter = {}
        _inject_prefixes_into_shorter_dict(current, shorter)
        self.assertEqual(len(shorter), 0)


class TestComputeSuggestions(unittest.TestCase):
    def test_compute_single_label(self):
        items = [{"label_name": "dog", "count": 10}]
        result = _compute_suggestions(items)
        self.assertEqual(len(result), 15)
        self.assertIn("dog", result[2])

    def test_compute_multiple_labels(self):
        items = [
            {"label_name": "dog", "count": 10},
            {"label_name": "door", "count": 5},
        ]
        result = _compute_suggestions(items)
        self.assertIn("do", result[1])

    def test_compute_invalid_label(self):
        items = [{"label_name": "", "count": 10}]
        result = _compute_suggestions(items)
        self.assertTrue(all(len(d) == 0 for d in result))

    def test_compute_negative_count(self):
        items = [{"label_name": "dog", "count": -1}]
        result = _compute_suggestions(items)
        self.assertTrue(all(len(d) == 0 for d in result))


class TestBatchUpdateSuggestions(unittest.TestCase):
    def test_update_success(self):
        mock_batch = Mock()
        prefix_dicts = [{"d": PrefixSuggestions()}]
        prefix_dicts[0]["d"].insert("dog", 10)
        updates, failures = _batch_update_suggestions(mock_batch, prefix_dicts)
        self.assertEqual(updates, 1)
        self.assertEqual(failures, 0)
        mock_batch.put_item.assert_called_once()

    def test_update_failure(self):
        mock_batch = Mock()
        mock_batch.put_item.side_effect = Exception("Error")
        prefix_dicts = [{"d": PrefixSuggestions()}]
        prefix_dicts[0]["d"].insert("dog", 10)
        updates, failures = _batch_update_suggestions(mock_batch, prefix_dicts)
        self.assertEqual(updates, 0)
        self.assertEqual(failures, 1)


class TestBatchDeleteObsoletePrefixes(unittest.TestCase):
    def test_delete_obsolete(self):
        mock_batch = Mock()
        existing = {"old"}
        prefix_dicts = [{}] * 15
        deletes, failures = _batch_delete_obsolete_prefixes(mock_batch, existing, prefix_dicts)
        self.assertEqual(deletes, 1)
        self.assertEqual(failures, 0)

    def test_delete_failure(self):
        mock_batch = Mock()
        mock_batch.delete_item.side_effect = Exception("Error")
        existing = {"old"}
        prefix_dicts = [{}] * 15
        deletes, failures = _batch_delete_obsolete_prefixes(mock_batch, existing, prefix_dicts)
        self.assertEqual(deletes, 0)
        self.assertEqual(failures, 1)

    def test_skip_empty_prefix(self):
        mock_batch = Mock()
        existing = {""}
        prefix_dicts = [{}] * 15
        deletes, failures = _batch_delete_obsolete_prefixes(mock_batch, existing, prefix_dicts)
        self.assertEqual(deletes, 0)


class TestUpdatePrefixSuggestionsTable(unittest.TestCase):
    def test_update_table_success(self):
        from update_prefix_suggestions import _update_prefix_suggestions_table
        mock_table = MagicMock()
        mock_table.scan.return_value = {"Items": []}
        prefix_dicts = [{"d": PrefixSuggestions()}] + [{}] * 14
        prefix_dicts[0]["d"].insert("dog", 10)
        
        _update_prefix_suggestions_table(mock_table, "d", prefix_dicts)
        mock_table.batch_writer.assert_called_once()

    def test_update_table_with_pagination(self):
        from update_prefix_suggestions import _update_prefix_suggestions_table
        mock_table = MagicMock()
        mock_table.scan.side_effect = [
            {"Items": [{"prefix": "old1"}], "LastEvaluatedKey": "key"},
            {"Items": [{"prefix": "old2"}]}
        ]
        prefix_dicts = [{}] * 15
        
        _update_prefix_suggestions_table(mock_table, "o", prefix_dicts)
        self.assertEqual(mock_table.scan.call_count, 2)

    def test_update_table_exception(self):
        from update_prefix_suggestions import _update_prefix_suggestions_table
        mock_table = MagicMock()
        mock_table.scan.side_effect = Exception("Scan error")
        prefix_dicts = [{}] * 15
        
        with self.assertRaises(Exception):
            _update_prefix_suggestions_table(mock_table, "d", prefix_dicts)


class TestQueryLabelsGenericException(unittest.TestCase):
    @patch('update_prefix_suggestions.logger')
    def test_query_generic_exception(self, mock_logger):
        mock_table = Mock()
        mock_table.meta.client.exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        mock_table.meta.client.exceptions.ProvisionedThroughputExceededException = type('ProvisionedThroughputExceededException', (Exception,), {})
        mock_table.meta.client.exceptions.RequestLimitExceeded = type('RequestLimitExceeded', (Exception,), {})
        mock_table.scan.side_effect = RuntimeError("Unexpected error")
        
        result = _query_labels_by_letter(mock_table, "d")
        self.assertIsNone(result)
        mock_logger.error.assert_called()


class TestInjectPrefixesException(unittest.TestCase):
    @patch('update_prefix_suggestions.logger')
    def test_inject_with_invalid_data(self, mock_logger):
        # Create a PrefixSuggestions with a counted_label that will cause an error on insert
        ps = PrefixSuggestions()
        ps.insert("test", 10)
        # Make the shorter dict's insert fail
        current = {"bad": ps}
        shorter = {"ba": Mock()}
        shorter["ba"].insert = Mock(side_effect=ValueError("Invalid insert"))
        _inject_prefixes_into_shorter_dict(current, shorter)
        mock_logger.warning.assert_called()


class TestLambdaHandler(unittest.TestCase):
    @patch("update_prefix_suggestions.boto3")
    def test_handler_success(self, mock_boto3):
        mock_batch = MagicMock()
        mock_table = Mock()
        mock_table.scan.return_value = {"Items": [{"label_name": "dog", "count": 10}]}
        mock_table.batch_writer.return_value = mock_batch
        
        mock_resource = Mock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_resource

        result = lambda_handler({}, {})
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("message", body)

    @patch("update_prefix_suggestions.boto3")
    def test_handler_failure(self, mock_boto3):
        mock_boto3.resource.side_effect = Exception("Connection error")
        result = lambda_handler({}, {})
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertIn("error", body)

    @patch("update_prefix_suggestions.boto3")
    def test_handler_with_failed_letters(self, mock_boto3):
        mock_table = Mock()
        mock_table.scan.side_effect = [Exception("Error")] * 26
        
        mock_resource = Mock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_resource

        result = lambda_handler({}, {})
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertGreater(len(body["failed_letters"]), 0)

    @patch("update_prefix_suggestions.boto3")
    @patch("update_prefix_suggestions._update_prefix_suggestions_table")
    def test_handler_letter_processing_exception(self, mock_update, mock_boto3):
        mock_table = Mock()
        mock_table.scan.return_value = {"Items": [{"label_name": "dog", "count": 10}]}
        mock_update.side_effect = Exception("Update error")
        
        mock_resource = Mock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_resource

        result = lambda_handler({}, {})
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(len(body["failed_letters"]), 26)

    @patch("update_prefix_suggestions.boto3")
    @patch("update_prefix_suggestions._query_labels_by_letter")
    def test_handler_with_none_response(self, mock_query, mock_boto3):
        mock_query.return_value = None
        mock_table = Mock()
        
        mock_resource = Mock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_resource

        result = lambda_handler({}, {})
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(len(body["failed_letters"]), 0)


if __name__ == "__main__":
    unittest.main()
