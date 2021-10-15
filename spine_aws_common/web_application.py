"""
Base Web Lambda application
"""
from abc import abstractmethod
from typing import List, Callable, Optional, Dict
import re
import json

from aws_lambda_powertools.event_handler.api_gateway import (
    Route,
    ResponseBuilder,
    Response,
)
from aws_lambda_powertools.utilities.data_classes.common import BaseProxyEvent

from spine_aws_common.lambda_application import LambdaApplication


class WebApplication(LambdaApplication):
    """
    Base class for Web Lambda applications
    """

    EVENT_TYPE = BaseProxyEvent

    def __init__(self, additional_log_config=None, load_ssm_params=False):
        super().__init__(
            additional_log_config=additional_log_config, load_ssm_params=load_ssm_params
        )
        self._routes: List[Route] = []
        self.configure_routes()

    def start(self):
        self.response = self._resolve().build(self.event)

    def _add_route(
        self,
        func: Callable,
        rule: str,
        method: str = "GET",
        cors: bool = None,
        compress: bool = False,
        cache_control: str = None,
    ):  # pylint: disable=too-many-arguments
        """
        Add a route
        """
        self._routes.append(
            Route(
                method=method,
                rule=self._compile_regex(rule),
                func=func,
                cors=cors,
                compress=compress,
                cache_control=cache_control,
            )
        )

    @staticmethod
    def _compile_regex(rule: str):
        """Precompile regex pattern"""
        rule_regex: str = re.sub(r"(<\w+>)", r"(?P\1.+)", rule)
        return re.compile(f"^{rule_regex}$")

    def _resolve(self) -> ResponseBuilder:
        """Resolve response"""
        for route in self._routes:
            if self.event.http_method.upper() != route.method:
                continue
            match: Optional[re.Match] = route.rule.match(self.event.path)
            if match:
                return self._call_route(route, match.groupdict())
        return ResponseBuilder(self.not_found_response())

    @staticmethod
    def _call_route(route: Route, args: Dict[str, str]) -> ResponseBuilder:
        """Actually call the matching route with any provided keyword arguments."""
        return ResponseBuilder(route.func(**args), route)

    @staticmethod
    def not_found_response() -> Response:
        """Default not found response (can be overridden)"""
        return Response(
            status_code=404,
            content_type="application/json",
            body=json.dumps({"message": "Not found"}),
        )

    @abstractmethod
    def configure_routes(self):
        """Override to configure API routes"""
