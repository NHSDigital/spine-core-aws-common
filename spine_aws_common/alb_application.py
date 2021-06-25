"""
Base ALB Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import ALBEvent
from spine_aws_common.lambda_application import LambdaApplication


class ALBApplication(LambdaApplication):
    """
    Base class for ALB Lambda applications
    """

    def process_event(self, event):
        return ALBEvent(event)

    def _get_internal_id(self):
        """
        Get internalID from the event
        """
        return self.event.headers.get("x-internal-id", self._create_new_internal_id())
