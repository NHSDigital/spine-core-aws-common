"""
Module for common application functionality for Lambda functions
"""
import os
import sys
from datetime import datetime, timezone
import uuid
from abc import abstractmethod
from spine_aws_common.logger import Logger, configureLoggingAdapter
from aws_lambda_powertools.utilities import parameters

DELIMITER = "_"


class LambdaApplication:
    """
    Base class for Lambda applications
    """

    def __init__(self, load_ssm_params=False):
        self.internal_id = None
        self.context = None
        self.event = None
        self.process_name = None

        self.system_config = self._load_system_config(load_ssm_params=load_ssm_params)

        self.log_object = self.get_logger()
        configureLoggingAdapter(self.log_object)

        self._log_coldstart()

        self.response = {"message": "Lambda application stopped"}

    def main(self, event, context):
        """
        Common entry point behaviour
        """
        try:
            self.context = context
            self.event = self.process_event(event)
            self.internal_id = self._get_internal_id()

            self.initialise()

            self.start()

        except InitialisationError as e:
            if self.log_object is None:
                print(e)
            else:
                self.log_object.writeLog("LAMBDAINIT001", None, {"message": e})
        except Exception as e:  # pylint:disable=broad-except
            if self.log_object is None:
                print(e)
                exit(1)
            else:
                self.log_object.writeLog(
                    "LAMBDA9999", sys.exc_info(), {"error": str(e)}
                )

        return self.response

    def get_logger(self):
        """
        Gets the default application logger. This may be overridden
        if a custom logger is required.
        """

        logger = Logger(processName=self.process_name)
        return logger

    def process_event(self, event):
        """
        Processes event object passed in by Lambda service
        Can be overridden to customise event parsing
        """
        return event

    @abstractmethod
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
        return self.event.get("internal_id", self._createNewInternalID())

    def _create_new_internal_id(self):
        """
        Creates an internalID
        """
        process_start_time = datetime.now(timezone.utc)
        internal_id = process_start_time.strftime("%Y%m%d%H%M%S%f")
        internal_id += DELIMITER + str(uuid.uuid4())[:6].upper()
        return internal_id

    def _load_system_config(self, load_ssm_params: bool):
        """
        Load common system configuration from Lambda ENV vars
        """
        try:
            env = os.environ.copy()
            self.process_name = env.get("AWS_LAMBDA_FUNCTION_NAME", "None")
            if load_ssm_params:
                config = parameters.get_parameters(f"/{self.process_name}")
                config.update(env)
                return config
            return env
        except Exception as e:
            raise InitialisationError(e)

    def _log_coldstart(self):
        log_params = {
            "aws_region": self.systemConfig.get("AWS_REGION"),
            "aws_execution_env": self.systemConfig.get("AWS_EXECUTION_ENV"),
            "function_name": self.process_name,
            "function_memory_size": self.systemConfig.get(
                "AWS_LAMBDA_FUNCTION_MEMORY_SIZE"
            ),
            "function_version": self.systemConfig.get("AWS_LAMBDA_FUNCTION_VERSION"),
        }
        self.log_object.writeLog("LAMBDA0001", None, log_params)


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
        super(InitialisationError, self).__init__()
        self.msg = msg
