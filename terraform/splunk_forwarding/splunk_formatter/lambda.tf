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
      SPLUNK_INDEX = var.splunk_index
    }
  }

  depends_on = [aws_cloudwatch_log_group.splunk_formatter]
}
