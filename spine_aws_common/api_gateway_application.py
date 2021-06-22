from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.event_handler.api_gateway import ApiGatewayResolver
from spine_aws_common import LambdaApplication


class APIGatewayApplication(LambdaApplication):
    """
    Base class for API Gateway Lambda applications
    """

    def process_event(self, event):
        return APIGatewayProxyEvent(event)

    def _getInternalID(self):
        """
        Get internalID from the event
        """
        return self.event.headers.get('x-internal-id', self._createNewInternalID())

    def initialise(self):
        """
        Application initialisation
        """
        self.app = ApiGatewayResolver()

    def start(self):
        """
        Start the application
        """
        self.response = self.app.resolve(self.event, self.context)
