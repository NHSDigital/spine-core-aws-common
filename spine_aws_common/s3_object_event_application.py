from aws_lambda_powertools.utilities.data_classes.s3_object_event import S3ObjectLambdaEvent
from spine_aws_common import LambdaApplication


class S3ObjectEventApplication(LambdaApplication):
    """
    Base class for S3 Object Event Lambda applications
    """

    def process_event(self, event):
        return S3ObjectLambdaEvent(event)

    def _getInternalID(self):
        """
        Get internalID from the event
        """
        return self._createNewInternalID()
