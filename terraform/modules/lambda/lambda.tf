data "archive_file" "function" {
  type        = "zip"
  source_dir  = "${path.module}/../../../spine_aws_common/mesh/mesh_implementation_lambdas"
  output_path = "${path.module}/${local.code_name}.zip"
}

resource "aws_lambda_function" "function" {
  function_name    = local.function_name
  filename         = data.archive_file.function.output_path
  handler          = "mesh_${replace(local.code_name, "-", "_")}_application_lambda.lambda_handler"
  runtime          = local.python_runtime
  timeout          = local.lambda_timeout
  source_code_hash = data.archive_file.function.output_base64sha256
  role             = aws_iam_role.function.arn

  depends_on = [aws_cloudwatch_log_group.function]
}
