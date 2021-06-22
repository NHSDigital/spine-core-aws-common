from aws_lambda_powertools.utilities.data_classes import CloudWatchLogsEvent
from spine_aws_common import LambdaApplication


class CloudwatchLogsApplication(LambdaApplication):
    """
    Base class for Cloudwatch Logs Lambda applications
    """

    def process_event(self, event):
        return CloudWatchLogsEvent(event)
