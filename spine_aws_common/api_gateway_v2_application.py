from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from aws_lambda_powertools.event_handler.api_gateway import ApiGatewayResolver, ProxyEventType
from spine_aws_common import LambdaApplication


class APIGatewayV2Application(LambdaApplication):
    """
    Base class for API Gateway V2 Lambda applications
    """

    def process_event(self, event):
        return APIGatewayProxyEventV2(event)

    def _getInternalID(self):
        """
        Get internalID from the event
        """
        return self.event.headers.get('x-internal-id', self._createNewInternalID())

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
