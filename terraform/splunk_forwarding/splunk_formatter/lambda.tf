resource "aws_lambda_function" "splunk_formatter" {
  function_name    = "${local.name}-lambda"
  filename         = data.archive_file.splunk_formatter_archive.output_path
  role             = aws_iam_role.splunk_formatter.arn
  handler          = "splunk_log_formatter.lambda_handler"
  source_code_hash = data.archive_file.splunk_formatter_archive.output_base64sha256
  runtime          = local.runtime
  timeout          = local.timeout
  memory_size      = local.memory_size
  layers           = [aws_lambda_layer_version.splunk_formatter_dependencies.arn]

  environment {
    variables = {
      SPLUNK_SOURCE_TYPE_PREFIX     = var.splunk_source_type_prefix
      SPLUNK_INDEXES_TO_LOGS_LEVELS = base64encode(jsonencode(var.splunk_indexes_to_logs_levels))
    }
  }

  depends_on = [aws_cloudwatch_log_group.splunk_formatter]
}
