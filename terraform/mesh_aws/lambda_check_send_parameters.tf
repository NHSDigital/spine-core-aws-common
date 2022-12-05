locals {
  check_send_parameters_name = "${local.name}-check-send-parameters"
}

resource "aws_security_group" "check_send_parameters" {
  count       = var.config.vpc_id == "" ? 0 : 1
  name        = local.check_send_parameters_name
  description = local.check_send_parameters_name
  vpc_id      = var.config.vpc_id

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
    prefix_list_ids = [data.aws_vpc_endpoint.s3.prefix_list_id]
  }
}

#tfsec:ignore:aws-lambda-enable-tracing
resource "aws_lambda_function" "check_send_parameters" {
  function_name    = local.check_send_parameters_name
  filename         = data.archive_file.mesh_aws_client.output_path
  handler          = "mesh_aws_client.mesh_check_send_parameters_application.lambda_handler"
  runtime          = local.python_runtime
  timeout          = 60
  source_code_hash = data.archive_file.mesh_aws_client.output_base64sha256
  role             = aws_iam_role.check_send_parameters.arn
  layers           = [aws_lambda_layer_version.mesh_aws_client_dependencies.arn]

  environment {
    variables = {
      Environment                     = local.name
      SEND_MESSAGE_STEP_FUNCTION_NAME = local.send_message_name
      use_secrets_manager             = var.config.use_secrets_manager
    }
  }

  dynamic "vpc_config" {
    for_each = var.config.vpc_enabled == true ? [var.config.vpc_enabled] : []
    content {
      subnet_ids         = var.config.subnet_ids
      security_group_ids = [aws_security_group.check_send_parameters[0].id]
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.check_send_parameters,
    aws_iam_role_policy_attachment.check_send_parameters
  ]
}

resource "aws_cloudwatch_log_group" "check_send_parameters" {
  name              = "/aws/lambda/${local.check_send_parameters_name}"
  retention_in_days = var.cloudwatch_retention_in_days
  kms_key_id        = aws_kms_key.mesh.arn
}

resource "aws_iam_role" "check_send_parameters" {
  name               = "${local.check_send_parameters_name}-role"
  description        = "${local.check_send_parameters_name}-role"
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
  name        = "${local.check_send_parameters_name}-policy"
  description = "${local.check_send_parameters_name}-policy"
  policy      = data.aws_iam_policy_document.check_send_parameters.json
}

#tfsec:ignore:aws-iam-no-policy-wildcards
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
      aws_cloudwatch_log_group.check_send_parameters.arn,
      "${aws_cloudwatch_log_group.check_send_parameters.arn}:*"
    ]
  }

  statement {
    sid    = "SSMDescribe"
    effect = "Allow"

    actions = [
      "ssm:DescribeParameters"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "SSMAllow"
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
    sid    = "S3Allow"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]

    resources = [
      aws_s3_bucket.mesh.arn,
      "${aws_s3_bucket.mesh.arn}/*"
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

resource "aws_iam_role_policy_attachment" "check_send_parameters_check_sfn" {
  role       = aws_iam_role.check_send_parameters.name
  policy_arn = aws_iam_policy.check_send_parameters_check_sfn.arn
}

resource "aws_iam_policy" "check_send_parameters_check_sfn" {
  name        = "${local.check_send_parameters_name}-check-sfn-policy"
  description = "${local.check_send_parameters_name}-check-sfn-policy"
  policy      = data.aws_iam_policy_document.check_send_parameters_check_sfn.json
}

#tfsec:ignore:aws-iam-no-policy-wildcards
data "aws_iam_policy_document" "check_send_parameters_check_sfn" {
  statement {
    sid    = "SFNList"
    effect = "Allow"

    actions = [
      "states:ListExecutions",
      "states:ListStateMachines"
    ]

    resources = [
      "arn:aws:states:eu-west-2:${data.aws_caller_identity.current.account_id}:stateMachine:*",
      aws_sfn_state_machine.get_messages.arn,
      aws_sfn_state_machine.send_message.arn
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
