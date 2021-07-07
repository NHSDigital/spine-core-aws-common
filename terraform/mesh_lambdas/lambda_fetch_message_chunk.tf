resource "aws_lambda_function" "fetch_message_chunk" {
  function_name    = "${local.name}-fetch-message-chunk"
  filename         = data.archive_file.mesh_implementation_lambdas.output_path
  handler          = "mesh_fetch_message_chunk_application_lambda.lambda_handler"
  runtime          = local.python_runtime
  timeout          = local.lambda_timeout
  source_code_hash = data.archive_file.mesh_implementation_lambdas.output_base64sha256
  role             = aws_iam_role.fetch_message_chunk.arn

  depends_on = [aws_cloudwatch_log_group.fetch_message_chunk]
}

resource "aws_cloudwatch_log_group" "fetch_message_chunk" {
  name              = "/aws/lambda/${local.name}-fetch-message-chunk"
  retention_in_days = 365
}

resource "aws_iam_role" "fetch_message_chunk" {
  name               = "${local.name}-fetch_message_chunk"
  description        = "${local.name}-fetch_message_chunk"
  assume_role_policy = data.aws_iam_policy_document.fetch_message_chunk_assume.json
}

data "aws_iam_policy_document" "fetch_message_chunk_assume" {
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

resource "aws_iam_role_policy_attachment" "fetch_message_chunk" {
  role       = aws_iam_role.fetch_message_chunk.name
  policy_arn = aws_iam_policy.fetch_message_chunk.arn
}

resource "aws_iam_policy" "fetch_message_chunk" {
  name        = "${local.name}-fetch_message_chunk"
  description = "${local.name}-fetch_message_chunk"
  policy      = data.aws_iam_policy_document.fetch_message_chunk.json
}

data "aws_iam_policy_document" "fetch_message_chunk" {
  statement {
    sid    = "CloudWatchAllow"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.fetch_message_chunk.arn}*"
    ]
  }
}
