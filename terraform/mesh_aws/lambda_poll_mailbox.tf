locals {
  poll_mailbox_name = "${local.name}-poll-mailbox"
}

resource "aws_security_group" "poll_mailbox" {
  count       = var.config.vpc_id == "" ? 0 : 1
  name        = local.poll_mailbox_name
  description = local.poll_mailbox_name
  vpc_id      = var.config.vpc_id

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.config.environment == "production" ? local.mesh_ips.production : local.mesh_ips.integration
  }

  egress {
    from_port = 443
    to_port   = 443
    protocol  = "tcp"
    security_groups = concat(
      var.config.aws_ssm_endpoint_sg_id,
      var.config.aws_sfn_endpoint_sg_id,
      var.config.aws_logs_endpoints_sg_id,
      var.config.aws_kms_endpoints_sg_id,
      var.config.aws_lambda_endpoints_sg_id
    )
  }
}

#tfsec:ignore:aws-lambda-enable-tracing
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
      Environment                     = local.name
      GET_MESSAGES_STEP_FUNCTION_NAME = local.get_messages_name
      use_secrets_manager             = var.config.use_secrets_manager
    }
  }

  dynamic "vpc_config" {
    for_each = var.config.vpc_enabled == true ? [var.config.vpc_enabled] : []
    content {
      subnet_ids         = var.config.subnet_ids
      security_group_ids = [aws_security_group.poll_mailbox[0].id]
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.poll_mailbox,
    aws_iam_role_policy_attachment.poll_mailbox
  ]
}

resource "aws_cloudwatch_log_group" "poll_mailbox" {
  name              = "/aws/lambda/${local.poll_mailbox_name}"
  retention_in_days = var.cloudwatch_retention_in_days
  kms_key_id        = aws_kms_key.mesh.arn
}

resource "aws_iam_role" "poll_mailbox" {
  name               = "${local.poll_mailbox_name}-role"
  description        = "${local.poll_mailbox_name}-role"
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
  name        = "${local.poll_mailbox_name}-policy"
  description = "${local.poll_mailbox_name}-policy"
  policy      = data.aws_iam_policy_document.poll_mailbox.json
}

#tfsec:ignore:aws-iam-no-policy-wildcards
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
    sid    = "EC2Interfaces"
    effect = "Allow"

    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface",
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy_attachment" "poll_mailbox_check_sfn" {
  role       = aws_iam_role.poll_mailbox.name
  policy_arn = aws_iam_policy.poll_mailbox_check_sfn.arn
}

resource "aws_iam_policy" "poll_mailbox_check_sfn" {
  name        = "${local.poll_mailbox_name}-check-sfn-policy"
  description = "${local.poll_mailbox_name}-check-sfn-policy"
  policy      = data.aws_iam_policy_document.poll_mailbox_check_sfn.json
}

#tfsec:ignore:aws-iam-no-policy-wildcards
data "aws_iam_policy_document" "poll_mailbox_check_sfn" {
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
