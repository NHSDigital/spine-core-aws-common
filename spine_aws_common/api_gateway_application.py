"""
Base API Gateway Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from spine_aws_common.web_application import WebApplication


class APIGatewayApplication(WebApplication):
    """
    Base class for API Gateway Lambda applications
    """

    EVENT_TYPE = APIGatewayProxyEvent

    def _get_internal_id(self):
        """
        Get internalID from the event
        """
        return self.event.headers.get("x-internal-id", self._create_new_internal_id())
