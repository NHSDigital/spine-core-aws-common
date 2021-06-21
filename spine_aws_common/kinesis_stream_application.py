import json

from aws_lambda_powertools.utilities.data_classes import KinesisStreamEvent
from spine_aws_common import BatchApplication


class KinesisStreamApplication(BatchApplication):
    """
    Base class for Kinesis Stream Lambda applications
    """

    def process_event(self, event):
        return KinesisStreamEvent(event)
