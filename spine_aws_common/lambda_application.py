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


class LambdaApplication:
    """
    Base class for Lambda applications
    """

    def __init__(self, load_ssm_params=False):
        self.internalID = None
        self.context = None
        self.event = None
        self.processName = None

        self.systemConfig = self._loadSystemConfig(
            load_ssm_params=load_ssm_params)

        self.logObject = self.getLogger()
        configureLoggingAdapter(self.logObject)

        self._log_coldstart()

        self.response = {'message': 'Lambda application stopped'}

    def main(self, event, context):
        """
        Common entry point behaviour
        """
        try:
            self.context = context
            self.event = self.process_event(event)
            self.internalID = self._getInternalID()

            self.initialise()

            self.start()

        except InitialisationError as e:
            if self.logObject is None:
                print(e)
            else:
                self.logObject.writeLog('LAMBDAINIT001', None, {'message': e})
        except Exception as e:  # pylint:disable=broad-except
            if self.logObject is None:
                print(e)
                exit(1)
            else:
                self.logObject.writeLog(
                    "LAMBDA9999", sys.exc_info(), {"error": str(e)})

        return self.response

    def getLogger(self):
        """
        Gets the default application logger. This may be overridden
        if a custom logger is required.
        """

        logger = Logger(processName=self.processName)
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

    def _getInternalID(self):
        """
        Get internalID from the event
        """
        return self.event.get('internal_id', self._createNewInternalID())

    def _createNewInternalID(self):
        """
        Creates an internalID
        """
        DELIMITER = '_'
        process_start_time = datetime.now(timezone.utc)
        internalID = process_start_time.strftime('%Y%m%d%H%M%S%f')
        internalID += DELIMITER + str(uuid.uuid4())[:6].upper()
        return internalID

    def _loadSystemConfig(self, load_ssm_params: bool):
        """
        Load common system configuration from Lambda ENV vars
        """
        try:
            env = os.environ.copy()
            self.processName = env.get('AWS_LAMBDA_FUNCTION_NAME', 'None')
            if load_ssm_params:
                config = parameters.get_parameters(f"/{self.processName}")
                config.update(env)
                return config
            return env
        except Exception as e:
            raise InitialisationError(e)

    def _log_coldstart(self):
        log_params = {
            "aws_region": self.systemConfig.get('AWS_REGION'),
            "aws_execution_env": self.systemConfig.get('AWS_EXECUTION_ENV'),
            "function_name": self.processName,
            "function_memory_size": self.systemConfig.get('AWS_LAMBDA_FUNCTION_MEMORY_SIZE'),
            "function_version": self.systemConfig.get('AWS_LAMBDA_FUNCTION_VERSION')
        }
        self.logObject.writeLog("LAMBDA0001", None, log_params)


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
