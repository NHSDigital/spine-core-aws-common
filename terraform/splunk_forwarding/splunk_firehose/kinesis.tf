resource "aws_kinesis_firehose_delivery_stream" "splunk_firehose" {
  name        = local.name
  destination = "splunk"

  splunk_configuration {
    hec_endpoint               = var.splunk_hec_endpoint
    hec_token                  = var.splunk_hec_token
    hec_acknowledgment_timeout = 300
    hec_endpoint_type          = "Event"
    s3_backup_mode             = "FailedEventsOnly"

    processing_configuration {
      enabled = "true"

      processors {
        type = "Lambda"

        parameters {
          parameter_name  = "LambdaArn"
          parameter_value = "${var.splunk_formatter.arn}:$LATEST"
        }
        parameters {
          parameter_name  = "RoleArn"
          parameter_value = aws_iam_role.splunk_firehose.arn
        }
      }
    }

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.splunk_firehose.name
      log_stream_name = aws_cloudwatch_log_stream.splunk_firehose.name
    }
  }

  s3_configuration {
    role_arn           = aws_iam_role.splunk_firehose.arn
    bucket_arn         = aws_s3_bucket.splunk_firehose.arn
    buffer_size        = 5
    buffer_interval    = 300
    compression_format = "GZIP"
    kms_key_arn        = var.kms_s3_key_arn
  }
}
