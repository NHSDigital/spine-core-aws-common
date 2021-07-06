"""
Base S3 Event Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import S3Event
from spine_aws_common.batch_application import BatchApplication


class S3EventApplication(BatchApplication):
    """
    Base class for S3 Event Lambda applications
    """

    EVENT_TYPE = S3Event

    def _get_internal_id_from_record(self, record):
        """
        Always create new internalID for S3 Events
        """
        return self._create_new_internal_id()
