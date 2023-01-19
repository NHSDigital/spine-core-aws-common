"""
Module for common application functionality for Lambda functions
"""
import os
from datetime import datetime, timezone
import uuid
from abc import abstractmethod
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.data_classes.common import DictWrapper
from spine_aws_common.utilities import StopWatch
from spine_aws_common.log.spinelogging import get_spine_logger

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
        self.internal_id: str = None
        self.system_config = self._load_system_config(load_ssm_params=load_ssm_params)
        self.configure_logging(additional_log_config)
        self._log_coldstart()

        self.response = None

    def configure_logging(self, additional_log_config):
        """Default logger is a spine config driven template k=v style logger"""
        process_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "None")
        self._logger = get_spine_logger(process_name, additional_log_config)
        self.log_object = DeprecatedLogger(python_logger=self._logger)

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
            self.internal_id = self._get_internal_id()

            self._log_start()

            self.initialise()

            self.start()

            self._log_end()

        except InitialisationError as e:
            self._logger.critical("LAMBDAINIT001", message=str(e), exc_info=True)
            raise e
        except Exception as e:  # pylint:disable=broad-except
            self._logger.error("LAMBDA9999", error=str(e), exc_info=True)
            raise e

        return self.response

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

    def _set_internal_id(self, value: str):
        """
        Sets internalID
        """
        self.internal_id = value

    def _get_internal_id(self) -> str:
        """
        Get internalID from the event
        """
        internal_id = None
        if self.event:
            internal_id = self.event.get("internal_id")
        if not internal_id:
            internal_id = self._create_new_internal_id()
        return internal_id

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
        self._logger.info(
            "LAMBDA0001",
            aws_region=self.system_config.get("AWS_REGION"),
            aws_execution_env=self.system_config.get("AWS_EXECUTION_ENV"),
            function_name=self.system_config.get("AWS_LAMBDA_FUNCTION_NAME", "None"),
            function_memory_size=self.system_config.get(
                "AWS_LAMBDA_FUNCTION_MEMORY_SIZE"
            ),
            function_version=self.system_config.get("AWS_LAMBDA_FUNCTION_VERSION"),
        )

    def _log_start(self):
        self._logger.info("LAMBDA0002", aws_request_id=self._get_aws_request_id())

    def _log_end(self):
        self._logger.info(
            "LAMBDA0003",
            duration=self.sync_timer.stop_the_clock(),
            aws_request_id=self._get_aws_request_id(),
        )

    def _get_aws_request_id(self):
        """Get the request id"""
        if hasattr(self.context, "aws_request_id"):
            aws_request_id = getattr(self.context, "aws_request_id", None)
            if aws_request_id:
                return aws_request_id
        elif isinstance(self.context, dict):
            return self.context.get("aws_request_id", "unknown")
        return "unknown"


class DeprecatedLogger:
    """Wrapper API for old spine logger"""

    def __init__(self, python_logger):
        self.logger = python_logger
        self.internal_id = None

    def set_internal_id(self, value):
        """Sets the internal id"""
        self.internal_id = value

    def write_log(self, log_reference, exc_info=None, log_dict=None):
        """Delegates spine-api logging to python logging"""
        if not log_dict:
            log_dict = {}
        self.logger.info(log_reference, exc_info=exc_info, **log_dict)


class InitialisationError(Exception):
    """
    Application initialisation error
    """

    def __init__(self, msg=None):
        super().__init__()
        self.msg = msg
