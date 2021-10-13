resource "aws_cloudwatch_log_group" "splunk_formatter" {
  name              = "/aws/lambda/${local.name}-lambda"
  retention_in_days = 30
  # TODO KMS
  # kms_key_id        = var.kms_key_arn
}
