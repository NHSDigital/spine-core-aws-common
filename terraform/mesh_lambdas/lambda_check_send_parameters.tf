resource "aws_lambda_function" "check_send_parameters" {
  function_name    = "${local.name}-check-send-parameters"
  filename         = data.archive_file.mesh_implementation_lambdas.output_path
  handler          = "mesh_check_send_parameters_application_lambda.lambda_handler"
  runtime          = local.python_runtime
  timeout          = local.lambda_timeout
  source_code_hash = data.archive_file.mesh_implementation_lambdas.output_base64sha256
  role             = aws_iam_role.check_send_parameters.arn

  depends_on = [aws_cloudwatch_log_group.check_send_parameters]
}

resource "aws_cloudwatch_log_group" "check_send_parameters" {
  name              = "/aws/lambda/${local.name}-check-send-parameters"
  retention_in_days = 365
}

resource "aws_iam_role" "check_send_parameters" {
  name               = "${local.name}-check_send_parameters"
  description        = "${local.name}-check_send_parameters"
  assume_role_policy = data.aws_iam_policy_document.check_send_parameters_assume.json
}

data "aws_iam_policy_document" "check_send_parameters_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"

      identifiers = [
        "lambda.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role_policy_attachment" "check_send_parameters" {
  role       = aws_iam_role.check_send_parameters.name
  policy_arn = aws_iam_policy.check_send_parameters.arn
}

resource "aws_iam_policy" "check_send_parameters" {
  name        = "${local.name}-check_send_parameters"
  description = "${local.name}-check_send_parameters"
  policy      = data.aws_iam_policy_document.check_send_parameters.json
}

data "aws_iam_policy_document" "check_send_parameters" {
  statement {
    sid    = "CloudWatchAllow"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.check_send_parameters.arn}*"
    ]
  }
}
