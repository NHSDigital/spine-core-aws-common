"""
Base API Gateway v2 Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from spine_aws_common.web_application import WebApplication


class APIGatewayV2Application(WebApplication):
    """
    Base class for API Gateway V2 Lambda applications
    """

    EVENT_TYPE = APIGatewayProxyEventV2

    def _get_internal_id(self):
        """
        Get internalID from the event
        """
        return self.event.headers.get("x-internal-id", self._create_new_internal_id())
