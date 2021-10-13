resource "aws_iam_role" "cloudwatch_subscription" {
  name               = "${local.name}-cloudwatch-role"
  description        = "${local.name}-cloudwatch-role"
  assume_role_policy = data.aws_iam_policy_document.cloudwatch_subscription_assume.json
}

data "aws_iam_policy_document" "cloudwatch_subscription_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"

      identifiers = [
        "logs.${data.aws_region.current.name}.amazonaws.com"
      ]
    }
  }
}

resource "aws_iam_role_policy_attachment" "cloudwatch_subscription" {
  role       = aws_iam_role.cloudwatch_subscription.name
  policy_arn = aws_iam_policy.cloudwatch_subscription.arn
}

resource "aws_iam_policy" "cloudwatch_subscription" {
  name        = "${local.name}-cloudwatch-policy"
  description = "${local.name}-cloudwatch-policy"
  policy      = data.aws_iam_policy_document.cloudwatch_subscription.json
}

data "aws_iam_policy_document" "cloudwatch_subscription" {
  statement {
    effect = "Allow"

    actions = [
      "iam:PassRole",
    ]

    resources = [
      aws_iam_role.cloudwatch_subscription.arn,
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "firehose:*", #TODO make specific?
    ]

    resources = [
      var.splunk_firehose.arn
    ]
  }
}
