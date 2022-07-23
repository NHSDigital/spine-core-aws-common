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
        return self._get_header("x-internal-id", self._create_new_internal_id())

    def _get_header(self, header, default=None):
        """
        Lower all the headers so they will be picked up if asked for regardless of case
        """
        headers = {k.lower(): v for k, v in self.event.headers.items()}
        return headers.get(header.lower(), default)
