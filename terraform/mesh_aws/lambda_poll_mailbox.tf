locals {
  poll_mailbox_name = "${local.name}-poll-mailbox"
}

resource "aws_lambda_function" "poll_mailbox" {
  function_name    = local.poll_mailbox_name
  filename         = data.archive_file.mesh_aws_client.output_path
  handler          = "mesh_aws_client.mesh_poll_mailbox_application.lambda_handler"
  runtime          = local.python_runtime
  timeout          = local.lambda_timeout
  source_code_hash = data.archive_file.mesh_aws_client.output_base64sha256
  role             = aws_iam_role.poll_mailbox.arn
  layers           = [aws_lambda_layer_version.mesh_aws_client_dependencies.arn]

  environment {
    variables = {
      Environment = local.name
    }
  }

  depends_on = [aws_cloudwatch_log_group.poll_mailbox]
}

resource "aws_cloudwatch_log_group" "poll_mailbox" {
  name              = "/aws/lambda/${local.poll_mailbox_name}"
  retention_in_days = var.cloudwatch_retention_in_days
}

resource "aws_iam_role" "poll_mailbox" {
  name               = local.poll_mailbox_name
  description        = local.poll_mailbox_name
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
  name        = local.poll_mailbox_name
  description = local.poll_mailbox_name
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

  statement {
    sid    = "SSMDescribe"
    effect = "Allow"

    actions = [
      "ssm:DescribeParameters"
    ]

    resources = [
      "arn:aws:ssm:eu-west-2:${data.aws_caller_identity.current.account_id}:parameter/${local.name}/*"
    ]
  }

  statement {
    sid    = "SSMGet"
    effect = "Allow"

    actions = [
      "ssm:GetParametersByPath"
    ]

    resources = [
      "arn:aws:ssm:eu-west-2:${data.aws_caller_identity.current.account_id}:parameter/${local.name}/*",
      "arn:aws:ssm:eu-west-2:${data.aws_caller_identity.current.account_id}:parameter/${local.name}"
    ]
  }

  statement {
    sid    = "KMSDecrypt"
    effect = "Allow"

    actions = [
      "kms:Decrypt"
    ]

    resources = [
      aws_kms_alias.mesh.target_key_arn
    ]
  }

  statement {
    sid    = "SFNList"
    effect = "Allow"

    actions = [
      "states:ListExecutions",
      "states:ListStateMachines"
    ]

    resources = [
      "arn:aws:states:eu-west-2:${data.aws_caller_identity.current.account_id}:stateMachine:*",
    ]
  }

  statement {
    sid    = "SFNAllow"
    effect = "Allow"

    actions = [
      "states:DescribeExecution",
    ]

    resources = [
      "${replace(aws_sfn_state_machine.get_messages.arn, "stateMachine", "execution")}*",
      "${replace(aws_sfn_state_machine.send_message.arn, "stateMachine", "execution")}*"
    ]
  }
}
