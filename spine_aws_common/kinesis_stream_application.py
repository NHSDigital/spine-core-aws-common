"""
Base Kinesis Stream Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import KinesisStreamEvent
from spine_aws_common.batch_application import BatchApplication


class KinesisStreamApplication(BatchApplication):
    """
    Base class for Kinesis Stream Lambda applications
    """

    EVENT_TYPE = KinesisStreamEvent
