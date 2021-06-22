from aws_lambda_powertools.utilities.data_classes import DynamoDBStreamEvent
from spine_aws_common import BatchApplication


class DynamoDBStreamsApplication(BatchApplication):
    """
    Base class for SQS Lambda applications
    """

    def process_event(self, event):
        return DynamoDBStreamEvent(event)

    def _getInternalIDfromRecord(self, record):
        """
        Always create new internalID for DynamoDB Streams event
        """
        return self._createNewInternalID()
