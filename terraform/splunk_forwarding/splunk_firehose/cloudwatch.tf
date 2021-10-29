resource "aws_cloudwatch_log_group" "splunk_firehose" {
  name              = "/aws/firehose/${local.name}"
  retention_in_days = 30
  kms_key_id        = var.kms_cloudwatch_key_arn
}

resource "aws_cloudwatch_log_stream" "splunk_firehose" {
  name           = local.name
  log_group_name = aws_cloudwatch_log_group.splunk_firehose.name
}
