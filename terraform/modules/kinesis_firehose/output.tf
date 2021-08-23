output "splunk_kinesis_firehose_stream_arn" {
  value = aws_kinesis_firehose_delivery_stream.splunk_kinesis_firehose.arn
}
