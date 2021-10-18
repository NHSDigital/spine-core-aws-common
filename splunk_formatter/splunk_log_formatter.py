""" Splunk Log Formatter """
import base64
import gzip
import io
import json
from base64 import b64decode
from typing import Optional

import boto3
from spine_aws_common import LambdaApplication


class SplunkLogFormatter(LambdaApplication):
    def __init__(self, additional_log_config=None, load_ssm_params=False) -> None:
        super().__init__(additional_log_config, load_ssm_params)
        self.firehose = boto3.client("firehose")
        self.splunk_source_type_prefix = ""
        self.splunk_indexes_to_logs_levels = ""

    def initialise(self) -> None:
        self.splunk_source_type_prefix = str(
            self.system_config.get("SPLUNK_SOURCE_TYPE_PREFIX")
        )
        self.splunk_indexes_to_logs_levels = self.get_splunk_indexes_to_logs_levels(
            str(self.system_config.get("SPLUNK_INDEXES_TO_LOGS_LEVELS"))
        )

    def start(self) -> None:
        stream_arn = self.event["deliveryStreamArn"]
        stream_name = stream_arn.split("/")[1]

        print(f"Records to process count: {len(self.event['records'])}")
        records = list(self.process_records(self.event["records"], stream_arn))

        data_by_record_id = {
            rec["recordId"]: self.create_reingestion_record(rec)
            for rec in self.event["records"]
        }
        put_record_batches = []
        records_to_reingest = []
        total_records_to_be_reingested = 0
        projected_size = 0
        for idx, rec in enumerate(records):
            if rec["result"] != "Ok":
                continue
            projected_size += len(rec["data"]) + len(rec["recordId"])
            # 6000000 instead of 6291456 to leave ample headroom for the stuff we didn't account for
            if projected_size > 6000000:
                total_records_to_be_reingested += 1
                records_to_reingest.append(
                    self.get_reingestion_record(data_by_record_id[rec["recordId"]])
                )
                records[idx]["result"] = "Dropped"
                del records[idx]["data"]

            # split out the record batches into multiple groups, 500 records at max per group
            if len(records_to_reingest) == 500:
                put_record_batches.append(records_to_reingest)
                records_to_reingest = []

        if len(records_to_reingest) > 0:
            # add the last batch
            put_record_batches.append(records_to_reingest)

        records_reingested_so_far = 0
        if len(put_record_batches) > 0:
            for record_batch in put_record_batches:
                self.put_records_to_firehose_stream(stream_name, record_batch, 0, 20)
                records_reingested_so_far += len(record_batch)
                print(
                    f"Reingested {records_reingested_so_far}/{total_records_to_be_reingested} records out of {len(self.event['records'])}"
                )
        else:
            print("No records to be reingested")

        print(f"Processed records count: {len(records)}")
        self.response = {"records": records}

    @staticmethod
    def get_source_type(log_group: str, prefix: Optional[str]) -> str:
        """returns the Splunk log source type, or the default"""
        if prefix:
            prefix = f"{prefix}:"
        else:
            prefix = ""

        if "CloudTrail" in log_group:
            return f"{prefix}aws:cloudtrail"

        if "VPC" in log_group:
            return f"{prefix}aws:cloudwatch_logs:vpcflow"

        return f"{prefix}aws:cloudwatch_logs"

    @staticmethod
    def get_splunk_indexes_to_logs_levels(index_mappings: str) -> "dict[str, str]":
        """base64 decode and then json decode the index mappings"""
        if index_mappings:
            return json.loads(b64decode(index_mappings))
        else:
            print("No Splunk Index to Log Level Mappings found")
            return {}

    @staticmethod
    def get_index(log_level: str, splunk_indexes_to_logs_levels: dict) -> Optional[str]:
        """returns the Splunk Index for a given log level or None, which means the
        reciever configured index will be used"""
        try:
            if splunk_indexes_to_logs_levels:
                return splunk_indexes_to_logs_levels[log_level.lower()]
        except KeyError:
            return None
        return None

    @staticmethod
    def get_level_of_log(log: str) -> str:
        """returns the log level of a log or unknown"""
        for level in ["INFO", "WARNING", "ERROR", "CRITICAL", "AUDIT"]:
            if f"Log_Level={level}" in log:
                return level

        # this will pick up some Lambda logs, identifying log types to indexes needs
        # more thought and understanding of requirements
        for level in ["START", "END", "REPORT"]:
            if level in log:
                return "AWS"

        return "UNKNOWN"

    @staticmethod
    def create_reingestion_record(original_record: dict) -> dict:
        return {"data": base64.b64decode(original_record["data"])}

    @staticmethod
    def get_reingestion_record(reingestion_record: dict) -> dict:
        return {"Data": reingestion_record["data"]}

    def transform_log_event(
        self, log_event: dict, arn: str, log_group: str, filter_name: str
    ) -> str:
        """Transform each log self.event.
        The default implementation below just extracts the message and appends a newline to it.

        Args:
            log_event (dict): The original log self.event. Structure is {"id": str, "timestamp": long, "message": str}
            arn: The ARN of the Kinesis Stream
            log_group: The Cloudwatch log group name
            filter_name: The Cloudwatch Subscription filter for the Stream

        Returns:
            str: The transformed log as JSON.
                In the case below, Splunk details are set as:
                    event = the log message
                    host = ARN of Firehose
                    index = the Splunk Index to be stored in
                    source = filter_name (of cloudwatch Log) contatinated with LogGroup Name
                    sourcetype = Splunk source type of the event
                    time = time of the Cloudwatch Log
        """
        output = {
            "event": log_event["message"],
            "host": arn,
            "source": f"{filter_name}:{log_group}",
            "sourcetype": self.get_source_type(
                log_group, self.splunk_source_type_prefix
            ),
            "time": str(log_event["timestamp"]),
        }

        # if we manage to lookup a specific index, add it to the output
        #   otherwise the Splunk Reciever configured default index will recieve the log
        index = self.get_index(
            self.get_level_of_log(log_event["message"]),
            self.splunk_indexes_to_logs_levels,
        )
        if index:
            output["index"] = index

        return json.dumps(output)

    def process_records(self, records: list, arn: str) -> dict:
        for r in records:
            data = base64.b64decode(r["data"])
            striodata = io.BytesIO(data)
            with gzip.GzipFile(fileobj=striodata, mode="r") as f:
                data = json.loads(f.read())

            recId = r["recordId"]
            if data["messageType"] == "CONTROL_MESSAGE":
                # CONTROL_MESSAGE are sent by CWL to check if the subscription is reachable.
                # They do not contain actual data.
                yield {"result": "Dropped", "recordId": recId}
            elif data["messageType"] == "DATA_MESSAGE":
                data = "".join(
                    [
                        self.transform_log_event(
                            event,
                            arn,
                            data["logGroup"],
                            data["subscriptionFilters"][0],
                        )
                        for event in data["logEvents"]
                    ]
                )
                data = base64.b64encode(data.encode("utf-8")).decode()
                yield {"data": data, "result": "Ok", "recordId": recId}
            else:
                yield {"result": "ProcessingFailed", "recordId": recId}

    def put_records_to_firehose_stream(
        self, stream_name: str, records: list, attempts_made: int, max_attempts: int
    ) -> None:
        failed_records = []
        codes = []
        error = ""
        # if put_record_batch throws for whatever reason, response['xx'] will error out,
        # adding a check for a valid response will prevent this
        response = None
        try:
            response = self.firehose.put_record_batch(
                DeliveryStreamName=stream_name, Records=records
            )
        except Exception as e:
            failed_records = records
            error = str(e)

        # if there are no failed_records (put_record_batch succeeded), iterate over the
        # response to gather results
        if not failed_records and response and response["FailedPutCount"] > 0:
            for idx, res in enumerate(response["RequestResponses"]):
                # (if the result does not have a key 'ErrorCode' OR if it does and is empty) => we do not need to re-ingest
                if "ErrorCode" not in res or not res["ErrorCode"]:
                    continue

                codes.append(res["ErrorCode"])
                failed_records.append(records[idx])

            error = f"Individual error codes: {','.join(codes)}"

        if len(failed_records) > 0:
            if attempts_made + 1 < max_attempts:
                print(
                    f"Some records failed while calling PutRecordBatch to Firehose stream, retrying: {error}"
                )
                self.put_records_to_firehose_stream(
                    stream_name, failed_records, attempts_made + 1, max_attempts
                )
            else:
                raise RuntimeError(
                    f"Could not put records after {str(max_attempts)} attempts: {error}"
                )


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = SplunkLogFormatter()


def lambda_handler(event, context):
    """Standard lambda_handler"""
    return app.main(event, context)
