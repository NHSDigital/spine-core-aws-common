"""
Base SNS Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import SNSEvent
from spine_aws_common.batch_application import BatchApplication


class SNSApplication(BatchApplication):
    """
    Base class for SNS Lambda applications
    """

    EVENT_TYPE = SNSEvent

    def _get_internal_id_from_record(self, record):
        """
        Get (or create new) internalID from record
        """
        if "internal_id" in record.sns.message_attributes:
            return record.sns.message_attributes["internal_id"].value
        return self._create_new_internal_id()
