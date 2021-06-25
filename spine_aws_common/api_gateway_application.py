"""
Base API Gateway Lambda application
"""
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from spine_aws_common.lambda_application import LambdaApplication


class APIGatewayApplication(LambdaApplication):
    """
    Base class for API Gateway Lambda applications
    """

    def process_event(self, event):
        return APIGatewayProxyEvent(event)

    def _get_internal_id(self):
        """
        Get internalID from the event
        """
        return self.event.headers.get("x-internal-id", self._create_new_internal_id())
