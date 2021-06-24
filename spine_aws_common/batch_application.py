"""
Base batch Lambda application
"""
from abc import abstractmethod

from spine_aws_common.lambda_application import LambdaApplication


class BatchApplication(LambdaApplication):
    """
    Base class for Batch Lambda applications
    """

    def __init__(self):
        super().__init__(self)
        self.records = None

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
            self.log_object.set_internal_id(self._get_internal_id_from_record(record))
            self.process_record(record)

    def _get_internal_id_from_record(self, record):
        """
        Get (or create new) internalID from record
        """
        return record.get("internal_id", self._create_new_internal_id())

    @abstractmethod
    def process_record(self, record):
        """
        Process a single record from the batch
        """
