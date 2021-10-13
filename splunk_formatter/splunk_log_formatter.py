""" Splunk Log Formatter """

import base64
import gzip
import io
import json

import boto3
from spine_aws_common import LambdaApplication


class SplunkLogFormatter(LambdaApplication):
    def __init__(self, additional_log_config=None, load_ssm_params=False):
        super().__init__(additional_log_config, load_ssm_params)
        self.firehose = boto3.client("firehose")
        self.index_mapping = {}
        self.default_source_type = None
        self.splunk_index = None

    def initialise(self):
        self.index_mapping = json.loads(
            str(self.system_config.get("INDEX_MAPPING", {}))
        )
        self.default_source_type = str(
            self.system_config.get("DEFAULT_SOURCE_TYPE", "aws:cloudwatch")
        )
        self.splunk_index = str(self.system_config.get("SPLUNK_INDEX"))

    def start(self):
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
        self.response = {
            "records": records,
        }

    def transform_log_event(self, log_event, arn, log_group, filter_name):
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
        return json.dumps(
            {
                "event": json.dumps(log_event["message"]),
                "host": arn,
                # TODO handle mapping of log level to indexes
                "index": self.splunk_index,
                # "index": self.get_index(
                #     log_event["message"], self.index_mapping, self.splunk_index
                # ),
                "source": f"{filter_name}:{log_group}",
                "sourcetype": self.get_source_type(log_group, self.default_source_type),
                "time": str(log_event["timestamp"]),
            }
        )

    @staticmethod
    def get_source_type(log_group: str, default_source_type: str) -> str:
        """returns the Splunk log source type, or the default"""
        if "CloudTrail" in log_group:
            return "aws:cloudtrail"

        if "VPC" in log_group:
            return "aws:cloudwatchlogs:vpcflow"

        return default_source_type

    @staticmethod
    def get_index(
        log_level: str, splunk_index_mapping: dict, default_index: str
    ) -> str:
        """returns the Splunk Index for a given log level, or the default"""
        try:
            return splunk_index_mapping[log_level]
        except KeyError:
            return default_index

    def process_records(self, records, arn):
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
        self, stream_name, records, attempts_made, max_attempts
    ):
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

    @staticmethod
    def create_reingestion_record(original_record):
        return {"data": base64.b64decode(original_record["data"])}

    @staticmethod
    def get_reingestion_record(reingestion_record):
        return {"Data": reingestion_record["data"]}


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = SplunkLogFormatter()


def lambda_handler(event, context):
    """Standard lambda_handler"""
    return app.main(event, context)
