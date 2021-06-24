"""
Base API Gateway v2 Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from aws_lambda_powertools.event_handler.api_gateway import (
    ApiGatewayResolver,
    ProxyEventType,
)
from spine_aws_common.lambda_application import LambdaApplication


class APIGatewayV2Application(LambdaApplication):
    """
    Base class for API Gateway V2 Lambda applications
    """

    def __init__(self):
        super().__init__(self)
        self.app = None

    def process_event(self, event):
        return APIGatewayProxyEventV2(event)

    def _get_internal_id(self):
        """
        Get internalID from the event
        """
        return self.event.headers.get("x-internal-id", self._create_new_internal_id())

    def initialise(self):
        """
        Application initialisation
        """
        self.app = ApiGatewayResolver(proxy_type=ProxyEventType.APIGatewayProxyEventV2)

    def start(self):
        """
        Start the application
        """
        self.response = self.app.resolve(self.event, self.context)
