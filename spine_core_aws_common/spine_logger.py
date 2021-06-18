import datetime
import traceback
import os

from spine_core_aws_common.log.spinelogging import get_log_base_config
from spine_core_aws_common.log.details import get_log_details, return_level
from spine_core_aws_common.log.constants import LoggingConstants as lc
from spine_core_aws_common.log.formatting import add_default_keys, evaluate_log_keys, create_placehold_log, create_log_line,\
    substitute_preamble_for_monitor
from spine_core_aws_common.log.thirdpartylogging import SEVERITY_INPUT_MAP, LoggingAdapter
from spine_core_aws_common.log.masking import mask_url

# pylint: disable=wrong-import-order
import logging as pythonlogging
# pylint: enable=wrong-import-order


class Logger(object):
    """
    Standard class for handling logging within cloud application
    Logs need to be prepared ready for splunk in the same way as
    Spine applications
    """

    _WRITEPLACEHOLDER = True  # Should a placeholder be written into operational logs

    def __init__(self, logBase=os.path.join(os.path.dirname(__file__), 'cloudlogbase.cfg'), processName='ANON',
                 severityThreshold='INFO', internalID=None):
        self._logBaseDict = get_log_base_config(log_base=logBase)

        self.processName = processName
        self.internalID = internalID
        self.severityThreshold = severityThreshold
        self.severityThresholdValue = return_level(severityThreshold)[0]
        self.dateFormat = '%d/%m/%Y %H:%M:%S'
        self.eventRowDict = {}

        self._logBaseCache = {}

    def writeLog(self, logReference='IGUTI9999', errorList=None,
                 logRowDict=None, severityThresholdOverride=None, processName=None):
        """
        The writing of the log allows the following information to be passed:
        :param logReference: this should resolve to a logReference within the logBase
        :type  logReference: str
        :param errorList: the output of a sys.exc_info() where an exception has been caught
        :param logRowDict - a dictionary of substitutions to be made against the logText in
        the logReference
        :type logRowDict: dict
        :param severityThresholdOverride: Not normally present - allows the standard log level to be
        over-ridden for this entry
        :param processName: Not normally present - allows the standard processName to be
        over-ridden for this entry

        The process for writing a log file entry is:
        Lookup the log reference information in the log base
        Exit out if the log level of the log is above that at which the user is set
        to log (e.g. if it is a DEBUG log and the user level is set to INFO)
        Create an audit version of the logRowDict containing sensitive data, and
        determine if an Audit entry is required
        """
        if logRowDict is None:
            logRowDict = {}

        logRowDict = {**logRowDict, **self.eventRowDict}

        if processName is None:
            processName = self.processName

        if not self._logBaseDict:
            self._printOutput(processName, logReference, logRowDict, errorList)
            return None

        log_details = get_log_details(logReference, self._logBaseDict, self._logBaseCache, pythonlogging=False)
        if not log_details or not log_details.check_log_severity_for_log(
                severityThresholdOverride,
                self.severityThreshold):
            return None

        # If not provided, set empty values for internalID and sessionId
        add_default_keys(logRowDict)
        evaluate_log_keys(log_details, logRowDict)

        timeNow = datetime.datetime.now()
        logPreamble = self._createLogPreamble(timeNow, log_details.log_level, processName, logReference)
        logRowDictMasked = mask_url(logRowDict)

        if log_details.audit_log_required:
            self._writeToCloudWatch(timeNow, logPreamble, log_details.log_text,
                                    logRowDictMasked, lc.LFR_AUDIT)
            if self._WRITEPLACEHOLDER:
                self._writeToCloudWatch(timeNow, logPreamble, create_placehold_log(logRowDictMasked),
                                        logRowDictMasked, lc.LFR_OPERATIONS)
        else:
            self._writeToCloudWatch(timeNow, logPreamble, log_details.log_text,
                                    logRowDictMasked, lc.LFR_OPERATIONS)

        if log_details.monitor_log_required:
            # Swap to Log_Level=MONITOR - will help prevent SALTing requirement
            # As Splunk may get matching CRC check for Audit and Monitor Log
            self._writeToCloudWatch(timeNow, substitute_preamble_for_monitor(logPreamble),
                                    log_details.log_text, logRowDictMasked, lc.LFR_NMS)

        if log_details.check_log_severity_for_crashdump(
                severityThresholdOverride,
                self.severityThreshold,
                errorList
        ):
            stubLogReference = lc.LR_CRASHDUMP
            stub_log_details = get_log_details(
                stubLogReference, self._logBaseDict, self._logBaseCache, pythonlogging=False)
            stubLogPreamble = self._createLogPreamble(
                timeNow, stub_log_details.log_level, processName, stubLogReference)

            # Write stub crashdump to spinevfmoperations, so that non-SC cleared staff can see a crash occurred
            self._writeToCloudWatch(timeNow, stubLogPreamble, stub_log_details.log_text,
                                    {'originalLogReference': logReference}, lc.LFR_OPERATIONS)

            # Write actual crashdump to spinevfmcrashdump
            self._writeToCloudWatch(timeNow, logPreamble, log_details.log_text,
                                    logRowDict, lc.LFR_CRASHDUMP, errorList)

        return log_details.log_text

    @staticmethod
    def _printOutput(processName, logReference, logRowDict, errorList):
        """
        Print out error details as no log object
        """
        printString = processName + ': Log Reference of ' + str(logReference)
        printString += ' raised but insufficient logging details'
        printString += ' identified to write to file.'
        print(printString)
        print('Error details ' + str(errorList))
        print('Log Parameters ' + str(logRowDict))

    def _createLogPreamble(self, timeNow, logLevel, processName, logReference):
        """
        Creates the string to form the initial part of any log message
        """
        logTimestampString = timeNow.strftime(self.dateFormat) + '.'
        logTimestampString += str(int(timeNow.microsecond / 1000)).rjust(3, '0')

        logPreamble = logTimestampString + ' Log_Level=' + logLevel
        logPreamble = logPreamble + ' Process=' + str(processName)
        if self.internalID:
            logPreamble = logPreamble + ' internalID=' + self.internalID
        return logPreamble + ' logReference=' + str(logReference)

    def _writeToCloudWatch(self, timeNow, logPreamble, logText, substitutionDict, logType, errorList=None):
        """
        Writes the log out to the standard out for Cloudwatch logging
        """
        _date = timeNow.strftime('%Y%m%d%H')

        if logType == lc.LFR_OPERATIONS:
            logIndex = 'spinevfmoperations'
        elif logType == lc.LFR_AUDIT:
            logIndex = 'spinevfmaudit'
        elif logType == lc.LFR_CRASHDUMP:
            logIndex = 'spinevfmcrashdump'
        elif logType == lc.LFR_NMS:
            logIndex = 'spinevfmmonitor'
        else:
            logIndex = 'spinevfmlog'

        logLine = create_log_line(logPreamble + ' Log_Index=' + logIndex, logText, substitutionDict)

        if errorList is not None:
            logLine = logLine + ' - ' + str(errorList[0:])
        logLine = logLine + '\r\n'

        print(logLine)
        if logType == lc.LFR_CRASHDUMP and errorList and len(errorList) >= 3:
            traceback.print_exception(errorList[0], errorList[1], errorList[2], None)

def configureLoggingAdapter(logObject):
    """
    Configure an adapter to allow libraries that use standard Python logging to output to our log files
    """
    rootLogger = pythonlogging.getLogger()
    rootLogger.handlers = []
    rootLogger.setLevel(SEVERITY_INPUT_MAP[logObject.severityThreshold])

    adapter = LoggingAdapter(logObject)
    rootLogger.addHandler(adapter)
    rootLogger.propagate = False
