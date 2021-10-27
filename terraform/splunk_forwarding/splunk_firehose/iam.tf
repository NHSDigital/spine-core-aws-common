resource "aws_iam_role" "splunk_firehose" {
  name               = "${local.name}-role"
  description        = "${local.name}-role"
  assume_role_policy = data.aws_iam_policy_document.splunk_firehose_assume.json
}

data "aws_iam_policy_document" "splunk_firehose_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"

      identifiers = [
        "firehose.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role_policy_attachment" "splunk_firehose" {
  role       = aws_iam_role.splunk_firehose.name
  policy_arn = aws_iam_policy.splunk_firehose.arn
}

resource "aws_iam_policy" "splunk_firehose" {
  name   = "${local.name}-policy"
  policy = data.aws_iam_policy_document.splunk_firehose.json
}

data "aws_iam_policy_document" "splunk_firehose" {
  statement {
    sid    = "CloudWatchAllow"
    effect = "Allow"

    actions = [
      "logs:PutLogEvents",
    ]

    resources = [
      aws_cloudwatch_log_group.splunk_firehose.arn,
      "${aws_cloudwatch_log_group.splunk_firehose.arn}:*"
    ]
  }

  statement {
    sid    = "S3Allow"
    effect = "Allow"

    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject",
    ]

    resources = [
      aws_s3_bucket.splunk_firehose.arn,
      "${aws_s3_bucket.splunk_firehose.arn}/*",
    ]
  }

  statement {
    sid    = "KMSAllow"
    effect = "Allow"

    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey*",
      "kms:ReEncrypt*",
    ]

    resources = [
      var.kms_s3_key_arn,
      var.kms_cloudwatch_key_arn
    ]
  }

  statement {
    sid    = "LambdaAllow"
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction",
      "lambda:GetFunctionConfiguration",
    ]

    resources = [
      "${var.splunk_formatter.arn}:$LATEST"
    ]
  }
}
