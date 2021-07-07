resource "aws_lambda_function" "poll_mailbox" {
  function_name    = "${local.name}-poll-mailbox"
  filename         = data.archive_file.mesh_implementation_lambdas.output_path
  handler          = "mesh_poll_mailbox_application_lambda.lambda_handler"
  runtime          = local.python_runtime
  timeout          = local.lambda_timeout
  source_code_hash = data.archive_file.mesh_implementation_lambdas.output_base64sha256
  role             = aws_iam_role.poll_mailbox.arn

  depends_on = [aws_cloudwatch_log_group.poll_mailbox]
}

resource "aws_cloudwatch_log_group" "poll_mailbox" {
  name              = "/aws/lambda/${local.name}-poll-mailbox"
  retention_in_days = 365
}

resource "aws_iam_role" "poll_mailbox" {
  name               = "${local.name}-poll_mailbox"
  description        = "${local.name}-poll_mailbox"
  assume_role_policy = data.aws_iam_policy_document.poll_mailbox_assume.json
}

data "aws_iam_policy_document" "poll_mailbox_assume" {
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

resource "aws_iam_role_policy_attachment" "poll_mailbox" {
  role       = aws_iam_role.poll_mailbox.name
  policy_arn = aws_iam_policy.poll_mailbox.arn
}

resource "aws_iam_policy" "poll_mailbox" {
  name        = "${local.name}-poll_mailbox"
  description = "${local.name}-poll_mailbox"
  policy      = data.aws_iam_policy_document.poll_mailbox.json
}

data "aws_iam_policy_document" "poll_mailbox" {
  statement {
    sid    = "CloudWatchAllow"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.poll_mailbox.arn}*"
    ]
  }
}
