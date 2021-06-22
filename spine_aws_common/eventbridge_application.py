from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent
from spine_aws_common import LambdaApplication


class EventbridgeApplication(LambdaApplication):
    """
    Base class for Eventbridge Lambda applications
    """

    def process_event(self, event):
        return EventBridgeEvent(event)
