locals {
  check_send_parameters_name = "${local.name}-check-send-parameters"
}

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
      Environment = local.name
    }
  }

  depends_on = [aws_cloudwatch_log_group.check_send_parameters]
}

resource "aws_cloudwatch_log_group" "check_send_parameters" {
  name              = "/aws/lambda/${local.check_send_parameters_name}"
  retention_in_days = var.cloudwatch_retention_in_days
}

resource "aws_iam_role" "check_send_parameters" {
  name               = local.check_send_parameters_name
  description        = local.check_send_parameters_name
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
  name        = local.check_send_parameters_name
  description = local.check_send_parameters_name
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
}
