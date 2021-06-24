"""
Base SES Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import SESEvent
from spine_aws_common import BatchApplication


class SESApplication(BatchApplication):
    """
    Base class for SES Lambda applications
    """

    def process_event(self, event):
        return SESEvent(event)
