from aws_lambda_powertools.utilities.data_classes import S3Event
from spine_aws_common import BatchApplication


class S3EventApplication(BatchApplication):
    """
    Base class for S3 Event Lambda applications
    """

    def process_event(self, event):
        return S3Event(event)

    def _getInternalIDfromRecord(self, record):
        """
        Always create new internalID for S3 Events
        """
        return self._createNewInternalID()
