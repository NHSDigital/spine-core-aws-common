locals {
  send_message_chunk_name = "${local.name}-send-message-chunk"
}

resource "aws_lambda_function" "send_message_chunk" {
  function_name    = local.send_message_chunk_name
  filename         = data.archive_file.mesh_aws_client.output_path
  handler          = "mesh_aws_client.mesh_send_message_chunk_application.lambda_handler"
  runtime          = local.python_runtime
  timeout          = 15 * 60 // 15 minutes
  source_code_hash = data.archive_file.mesh_aws_client.output_base64sha256
  role             = aws_iam_role.send_message_chunk.arn
  layers           = [aws_lambda_layer_version.mesh_aws_client_dependencies.arn]

  environment {
    variables = {
      Environment = local.name
    }
  }

  depends_on = [aws_cloudwatch_log_group.send_message_chunk]
}

resource "aws_cloudwatch_log_group" "send_message_chunk" {
  name              = "/aws/lambda/${local.send_message_chunk_name}"
  retention_in_days = var.cloudwatch_retention_in_days
}

resource "aws_iam_role" "send_message_chunk" {
  name               = local.send_message_chunk_name
  description        = local.send_message_chunk_name
  assume_role_policy = data.aws_iam_policy_document.send_message_chunk_assume.json
}

data "aws_iam_policy_document" "send_message_chunk_assume" {
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

resource "aws_iam_role_policy_attachment" "send_message_chunk" {
  role       = aws_iam_role.send_message_chunk.name
  policy_arn = aws_iam_policy.send_message_chunk.arn
}

resource "aws_iam_policy" "send_message_chunk" {
  name        = local.send_message_chunk_name
  description = local.send_message_chunk_name
  policy      = data.aws_iam_policy_document.send_message_chunk.json
}

data "aws_iam_policy_document" "send_message_chunk" {
  statement {
    sid    = "CloudWatchAllow"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.send_message_chunk.arn}*"
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
    sid    = "S3Allow"
    effect = "Allow"

    actions = [
      "s3:GetObject"
    ]

    resources = [
      aws_s3_bucket.mesh.arn,
      "${aws_s3_bucket.mesh.arn}/*"
    ]
  }
}
