"""
Base SQS Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import SQSEvent
from spine_aws_common import BatchApplication


class SQSApplication(BatchApplication):
    """
    Base class for SQS Lambda applications
    """

    def process_event(self, event):
        return SQSEvent(event)

    def _get_internal_id_from_record(self, record):
        """
        Get (or create new) internalID from record
        """
        if "internal_id" in record.message_attributes:
            return record.message_attributes["internal_id"]["stringValue"]
        return self._create_new_internal_id()
