output "splunk_kinesis_firehose_stream_arn" {
  value = aws_kinesis_firehose_delivery_stream.splunk_kinesis_firehose.arn
}

output "cloudwatch_to_firehose_role" {
  value = aws_iam_role.cloudwatch_to_firehose_trust.arn
}
