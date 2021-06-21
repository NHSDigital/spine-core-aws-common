"""
Module for common application functionality for Lambda functions
"""
import os
import sys
from datetime import datetime, timezone
import uuid
import json
from abc import abstractmethod
from spinecore.logger import Logger, configureLoggingAdapter

class LambdaApplication(object):
    """
    Base class for Lambda applications
    """


    def __init__(self, event, context):
        self.logObject = None
        self.systemConfig = None
        self.event = event
        self.context = context
        self.internalID = None


    def main(self):
        """
        Common entry point behaviour
        """
        try:
            self._loadSystemConfig()
            self.internalID = self._getInternalID()
            # Setup log object
            self.logObject = self.getLogger()
            configureLoggingAdapter(self.logObject)

            self.initialise()

            self.start()

        except InitialisationError as e:
            if self.logObject is None:
                print(e)
            else:
                self.logObject.writeLog('LAMBDAINIT001', None, {'message': e})
        except Exception as e: #pylint:disable=broad-except
            if self.logObject is None:
                print(e)
                exit(1)
            else:
                self.logObject.writeLog("LAMBDA9999", sys.exc_info(), {"error": str(e)})

        return {
            'message': 'Lambda application stopped'
        }


    def getLogger(self):
        """
        Gets the default application logger. This may be overridden
        if a custom logger is required.
        """

        logger = Logger(processName=self.context.function_name, internalID=self.internalID)
        return logger


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


    def addInternalID(self, messageBody, createInternalID=False):
        """
        Helper for json objects (e.g. SQS objects), adds internalID from self or creates new one
        """
        if createInternalID:
            internalID = self._createNewInternalID()
        else:
            internalID = self.internalID
        messageBody.set('internal_id', internalID)


    def _getInternalID(self):
        """
        Get internalID from the event
        """
        if 'headers' in self.event:
            self.internalID = self.event.get('headers', {}).get('request_id')
            if self.internalID:
                return
        elif self.event.get('Records') and self.event['Records'][0].get('eventSource') == 'aws:sqs':
            queueMessageBody = json.loads(self.event['Records'][0].get('body', {}))
            self.internalID = queueMessageBody.get('internal_id')
            if self.internalID:
                return
        self.internalID = self._createNewInternalID()


    def _createNewInternalID(self):
        """
        Creates an internalID
        """
        DELIMITER = '_'
        process_start_time = datetime.now(timezone.utc)
        internalID = process_start_time.strftime('%Y%m%d%H%M%S%f')
        internalID += DELIMITER + str(uuid.uuid4())[:6].upper()
        return internalID


    def _loadSystemConfig(self):
        """
        Load common system configuration from Lambda ENV vars
        """
        try:
            self.systemConfig = os.environ.copy()
        except Exception as e:
            raise InitialisationError(e)


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
