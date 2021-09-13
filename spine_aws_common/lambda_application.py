"""
Module for common application functionality for Lambda functions
"""
import os
import sys
from datetime import datetime, timezone
import uuid
from abc import abstractmethod
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.data_classes.common import DictWrapper
from aws_lambda_powertools.utilities.typing.lambda_context import LambdaContext
from spine_aws_common.logger import Logger, configure_logging_adapter
from spine_aws_common.utilities import StopWatch

DELIMITER = "_"


# pylint: disable=too-many-instance-attributes
class LambdaApplication:
    """
    Base class for Lambda applications
    """

    # Base class will always return event in same format
    EVENT_TYPE = DictWrapper

    def __init__(self, additional_log_config=None, load_ssm_params=False):
        self.context = None
        self.event = None
        self.sync_timer = None

        self.system_config = self._load_system_config(load_ssm_params=load_ssm_params)

        self.log_object = self.get_logger(additional_log_config=additional_log_config)
        configure_logging_adapter(self.log_object)

        self._log_coldstart()

        self.response = None

    def main(self, event, context):
        """
        Common entry point behaviour
        """
        self.response = {"message": "Lambda application stopped"}
        try:
            self.sync_timer = StopWatch()
            self.sync_timer.start_the_clock()
            self.context = context
            self.event = self.process_event(event)
            self.log_object.set_internal_id(self._get_internal_id())

            self._log_start()

            self.initialise()

            self.start()

            self._log_end()

        except InitialisationError as e:
            if self.log_object is None:
                print(e)
            else:
                self.log_object.write_log("LAMBDAINIT001", None, {"message": e})
            raise e
        except Exception as e:  # pylint:disable=broad-except
            if self.log_object is None:
                print(e)
            else:
                self.log_object.write_log(
                    "LAMBDA9999", sys.exc_info(), {"error": str(e)}
                )
            raise e

        return self.response

    def get_logger(self, additional_log_config=None):
        """
        Gets the default application logger. This may be overridden
        if a custom logger is required.
        """

        logger = Logger(
            process_name=self.system_config.get("AWS_LAMBDA_FUNCTION_NAME", "None"),
            additional_log_config=additional_log_config,
        )
        return logger

    def process_event(self, event):
        """
        Processes event object passed in by Lambda service
        Can be overridden to customise event parsing
        """
        return self.EVENT_TYPE(event)

    def initialise(self):
        """
        Application initialisation
        """

    @abstractmethod
    def start(self):
        """
        Start the application
        """

    def _get_internal_id(self):
        """
        Get internalID from the event
        """
        return self.event.get("internal_id") or self._create_new_internal_id()

    @staticmethod
    def _create_new_internal_id():
        """
        Creates an internalID
        """
        process_start_time = datetime.now(timezone.utc)
        internal_id = process_start_time.strftime("%Y%m%d%H%M%S%f")
        internal_id += DELIMITER + str(uuid.uuid4())[:6].upper()
        return internal_id

    @staticmethod
    def _load_system_config(load_ssm_params: bool):
        """
        Load common system configuration from Lambda ENV vars
        """
        try:
            env = os.environ.copy()
            process_name = env.get("AWS_LAMBDA_FUNCTION_NAME", "None")
            if load_ssm_params:
                config = parameters.get_parameters(
                    f"/{process_name}", force_fetch=True, decrypt=True
                )
                config.update(env)
                return config
            return env
        except Exception as e:
            raise InitialisationError(e) from e

    def _log_coldstart(self):
        log_params = {
            "aws_region": self.system_config.get("AWS_REGION"),
            "aws_execution_env": self.system_config.get("AWS_EXECUTION_ENV"),
            "function_name": self.system_config.get("AWS_LAMBDA_FUNCTION_NAME", "None"),
            "function_memory_size": self.system_config.get(
                "AWS_LAMBDA_FUNCTION_MEMORY_SIZE"
            ),
            "function_version": self.system_config.get("AWS_LAMBDA_FUNCTION_VERSION"),
        }
        self.log_object.write_log("LAMBDA0001", None, log_params)

    def _log_start(self):
        log_params = {
            "aws_request_id": self._get_aws_request_id(),
        }
        self.log_object.write_log("LAMBDA0002", None, log_params)

    def _log_end(self):
        log_params = {
            "duration": self.sync_timer.stop_the_clock(),
            "aws_request_id": self._get_aws_request_id(),
        }
        self.log_object.write_log("LAMBDA0003", None, log_params)

    def _get_aws_request_id(self):
        """Get the request id"""
        if isinstance(self.context, LambdaContext) and getattr(
            self.context, "aws_request_id", None
        ):
            return self.context.aws_request_id
        if isinstance(self.context, dict):
            return self.context.get("aws_request_id", "unknown")
        return "unknown"


def overrides(base_class):
    """
    Decorator used to specify that a method overrides a base class method
    """

    def decorate(method):
        """
        Override assertion
        """
        assert method.__name__ in dir(base_class)
        return method

    return decorate


class InitialisationError(Exception):
    """
    Application initialisation error
    """

    def __init__(self, msg=None):
        super().__init__()
        self.msg = msg
