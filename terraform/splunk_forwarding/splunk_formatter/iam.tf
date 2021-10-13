resource "aws_iam_role" "splunk_formatter" {
  name               = "${local.name}-role"
  description        = "${local.name}-role"
  assume_role_policy = data.aws_iam_policy_document.splunk_formatter_assume.json
}

data "aws_iam_policy_document" "splunk_formatter_assume" {
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

resource "aws_iam_role_policy_attachment" "splunk_formatter" {
  role       = aws_iam_role.splunk_formatter.name
  policy_arn = aws_iam_policy.splunk_formatter.arn
}

resource "aws_iam_policy" "splunk_formatter" {
  name        = "${local.name}-policy"
  description = "${local.name}-policy"
  policy      = data.aws_iam_policy_document.splunk_formatter.json
}

data "aws_iam_policy_document" "splunk_formatter" {
  statement {
    sid    = "CloudWatchAllow"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      aws_cloudwatch_log_group.splunk_formatter.arn,
      "${aws_cloudwatch_log_group.splunk_formatter.arn}:*"
    ]
  }

  statement {
    sid    = "KenesisAllow"
    effect = "Allow"

    actions = [
      "firehose:PutRecordBatch",
    ]

    resources = [
      var.splunk_firehose.arn
    ]
  }
}
