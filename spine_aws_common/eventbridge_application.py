"""
Base Eventbridge Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent
from spine_aws_common.lambda_application import LambdaApplication


class EventbridgeApplication(LambdaApplication):
    """
    Base class for Eventbridge Lambda applications
    """

    EVENT_TYPE = EventBridgeEvent
