"""
Base DynamoDB streams Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import DynamoDBStreamEvent
from spine_aws_common.batch_application import BatchApplication


class DynamoDBStreamsApplication(BatchApplication):
    """
    Base class for SQS Lambda applications
    """

    EVENT_TYPE = DynamoDBStreamEvent

    def _get_internal_id_from_record(self, record):
        """
        Always create new internalID for DynamoDB Streams event
        """
        return self._create_new_internal_id()
