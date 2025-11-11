"""
Lambda function to update prefix suggestions.
"""

import json
import logging
import boto3
import string
import heapq
import copy
from functools import total_ordering

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_MAX_SUGGESTIONS = 10
_MAX_PREFIX_LENGTH = 15
_LABEL_COUNTS_TABLE = "label_counts"
_PREFIX_SUGGESTIONS_TABLE = "prefix_suggestions"


@total_ordering
class CountedLabel:
    def __init__(self, label_name, count):
        self.label_name = label_name
        self.count = count

    def __lt__(self, other):
        return self.count < other.count

    def __eq__(self, other):
        return self.count == other.count and self.label_name == other.label_name


class PrefixSuggestions:
    def __init__(self):
        self.counted_labels = []
        self.overall_count = 0

    def insert(self, label_name, count):
        if not isinstance(label_name, str) or not label_name:
            raise ValueError(f"Invalid label_name: {label_name}")
        if not isinstance(count, int) or count < 0:
            raise ValueError(f"Invalid count: {count}")

        self.overall_count += count
        heapq.heappush(self.counted_labels, CountedLabel(label_name, count))

        if len(self.counted_labels) > _MAX_SUGGESTIONS:
            heapq.heappop(self.counted_labels)

    def __deepcopy__(self, memo):
        new_obj = PrefixSuggestions()
        new_obj.overall_count = self.overall_count
        new_obj.counted_labels = [
            CountedLabel(label.label_name, label.count) for label in self.counted_labels
        ]
        return new_obj


def _query_labels_by_letter(table, letter):
    """Query DynamoDB for labels starting with a letter."""
    try:
        items = []
        scan_kwargs = {
            "FilterExpression": "begins_with(label_name, :letter)",
            "ExpressionAttributeValues": {":letter": letter.lower()},
        }

        while True:
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

            if "LastEvaluatedKey" not in response:
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        return {"Items": items}

    except table.meta.client.exceptions.ResourceNotFoundException as e:
        logger.error(f"Table or index not found for letter '{letter}': {e}")
        return None
    except (
        table.meta.client.exceptions.ProvisionedThroughputExceededException,
        table.meta.client.exceptions.RequestLimitExceeded,
    ) as e:
        logger.warning(f"DynamoDB throttling for letter '{letter}': {e}")
        return None
    except Exception as e:
        logger.error(f"DynamoDB scan failed for letter '{letter}': {e}")
        return None


def _inject_prefixes_into_shorter_dict(current_prefix_dict, shorter_prefix_dict):
    for prefix in current_prefix_dict:
        try:
            if not prefix:
                continue
            shorter_prefix = prefix[:-1]

            if shorter_prefix not in shorter_prefix_dict:
                shorter_prefix_dict[shorter_prefix] = copy.deepcopy(
                    current_prefix_dict[prefix]
                )
                continue

            for counted_label in current_prefix_dict[prefix].counted_labels:
                shorter_prefix_dict[shorter_prefix].insert(
                    counted_label.label_name, counted_label.count
                )
        except (ValueError, KeyError, AttributeError) as e:
            logger.warning(f"Failed to inject prefix '{prefix}': {e}")
            continue


def _compute_suggestions(items):
    """Process all labels starting with a given letter."""
    prefix_dicts = [dict() for _ in range(1, _MAX_PREFIX_LENGTH + 1)]

    for item in items:
        label_name = item["label_name"]
        count = int(item["count"])

        if not label_name or len(label_name) < 1 or count < 0:
            logger.warning(f"Invalid label or count: {item}")
            continue

        start_prefix = label_name[:_MAX_PREFIX_LENGTH]
        prefix_dict = prefix_dicts[len(start_prefix) - 1]

        if start_prefix not in prefix_dict:
            prefix_dict[start_prefix] = PrefixSuggestions()

        prefix_dict[start_prefix].insert(label_name, count)

    for length in range(_MAX_PREFIX_LENGTH - 1, 0, -1):
        current_prefix_dict = prefix_dicts[length]
        shorter_prefix_dict = prefix_dicts[length - 1]

        _inject_prefixes_into_shorter_dict(current_prefix_dict, shorter_prefix_dict)

    return prefix_dicts


def _batch_update_suggestions(batch, prefix_dicts):
    """Update suggestions using batch writer."""
    updates_count = 0
    failure_count = 0
    for prefix_dict in prefix_dicts:
        for prefix, suggestions_obj in prefix_dict.items():
            try:
                suggestions = [
                    counted_label.label_name
                    for counted_label in heapq.nlargest(
                        _MAX_SUGGESTIONS, suggestions_obj.counted_labels
                    )
                ]

                batch.put_item(Item={"prefix": prefix, "suggestions": suggestions})
                updates_count += 1
            except Exception as e:
                logger.warning(f"Failed to update prefix '{prefix}': {e}")
                failure_count += 1

    return updates_count, failure_count


def _batch_delete_obsolete_prefixes(batch, existing_prefixes, prefix_dicts):
    """Delete obsolete prefixes using batch writer."""
    deletes_count = 0
    failure_count = 0
    for prefix in existing_prefixes:
        shortened_prefix = prefix[:_MAX_PREFIX_LENGTH]
        if len(shortened_prefix) == 0:
            continue

        if shortened_prefix not in prefix_dicts[len(shortened_prefix) - 1]:
            try:
                batch.delete_item(Key={"prefix": prefix})
                deletes_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete prefix '{prefix}': {e}")
                failure_count += 1
    return deletes_count, failure_count


def _update_prefix_suggestions_table(table, letter, prefix_dicts):
    try:
        # Get existing prefixes for this letter
        existing_prefixes = set()
        scan_kwargs = {
            "FilterExpression": "begins_with(prefix, :letter)",
            "ExpressionAttributeValues": {":letter": letter},
        }

        while True:
            response = table.scan(**scan_kwargs)
            existing_prefixes.update(
                item["prefix"] for item in response.get("Items", [])
            )

            if "LastEvaluatedKey" not in response:
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        logger.debug(
            f"Found {len(existing_prefixes)} existing prefixes for letter '{letter}'"
        )

        updates_count = 0
        deletes_count = 0

        # Update/add new suggestions
        with table.batch_writer() as batch:
            updates_count, update_failures = _batch_update_suggestions(
                batch, prefix_dicts
            )
            deletes_count, delete_failures = _batch_delete_obsolete_prefixes(
                batch, existing_prefixes, prefix_dicts
            )

        logger.info(
            f"Updated {updates_count}/{updates_count + update_failures} prefixes,"
            f" deleted {deletes_count}/{deletes_count + delete_failures} "
            f"prefixes for letter '{letter}'"
        )

    except Exception as e:
        logger.error(
            f"Error updating prefix suggestions table for letter '{letter}': {e}"
        )
        raise


def lambda_handler(event, context):
    """
    Update prefix suggestions by processing label counts.

    Args:
        event: CloudWatch Events event
        context: Lambda context object

    Returns:
        dict: Response with status code and message
    """
    logger.info("Update prefix suggestions triggered")

    failed_letters = []

    try:
        logger.info("Initializing DynamoDB connection")
        dynamodb = boto3.resource("dynamodb")
        label_counts_table = dynamodb.Table(_LABEL_COUNTS_TABLE)
        prefix_suggestions_table = dynamodb.Table(_PREFIX_SUGGESTIONS_TABLE)

        # Currently not executed parallelly to avoid massive memory consumption
        for letter in string.ascii_lowercase:
            try:
                response = _query_labels_by_letter(label_counts_table, letter)
                if response is None:
                    continue
                logger.debug(
                    f"Found {len(response['Items'])} labels for letter '{letter}'"
                )

                logger.debug(f"Computing suggestions for letter '{letter}'")
                letter_prefix_dict = _compute_suggestions(response["Items"])
                logger.debug(f"Computed suggestions for letter '{letter}'")

                logger.debug(f"Updating prefix_suggestions table for letter '{letter}'")
                _update_prefix_suggestions_table(
                    prefix_suggestions_table, letter, letter_prefix_dict
                )
                logger.debug(f"Updated prefix_suggestions table for letter '{letter}'")

            except Exception as e:
                logger.error(f"Error processing letter '{letter}': {e}")
                failed_letters.append(letter)
                continue

        logger.info("Completed processing all letter prefixes successfully")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Prefix suggestions update completed",
                    "failed_letters": failed_letters,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error updating prefix suggestions: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "details": str(e)}),
        }
