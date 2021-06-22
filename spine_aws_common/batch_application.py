from abc import abstractmethod

from spine_aws_common import LambdaApplication


class BatchApplication(LambdaApplication):
    """
    Base class for Batch Lambda applications
    """

    def initialise(self):
        """
        Application initialisation
        """
        self.records = self.event.records

    def start(self):
        """
        Start the application
        """
        for record in self.records:
            self.internalID = self._getInternalIDfromRecord(record)
            self.process_record(record)

    def _getInternalIDfromRecord(self, record):
        """
        Get (or create new) internalID from record
        """
        return record.get('internal_id', self._createNewInternalID())

    @abstractmethod
    def process_record(self, record):
        """
        Process a single record from the batch
        """
