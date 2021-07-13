"""
Base ALB Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import ALBEvent
from spine_aws_common.web_application import WebApplication


class ALBApplication(WebApplication):
    """
    Base class for ALB Lambda applications
    """

    EVENT_TYPE = ALBEvent

    def _get_internal_id(self):
        """
        Get internalID from the event
        """
        return self.event.headers.get("x-internal-id", self._create_new_internal_id())
