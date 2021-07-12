"""
Base Cloudwatch Logs Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import CloudWatchLogsEvent
from spine_aws_common.lambda_application import LambdaApplication


class CloudwatchLogsApplication(LambdaApplication):
    """
    Base class for Cloudwatch Logs Lambda applications
    """

    EVENT_TYPE = CloudWatchLogsEvent
