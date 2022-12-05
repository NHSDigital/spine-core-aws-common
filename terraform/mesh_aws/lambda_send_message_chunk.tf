locals {
  send_message_chunk_name = "${local.name}-send-message-chunk"
}

resource "aws_security_group" "send_message_chunk" {
  count       = var.config.vpc_id == "" ? 0 : 1
  name        = local.send_message_chunk_name
  description = local.send_message_chunk_name
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
      var.config.aws_s3_endpoint_sg_id,
      var.config.aws_ssm_endpoint_sg_id,
      var.config.aws_logs_endpoints_sg_id,
      var.config.aws_kms_endpoints_sg_id,
      var.config.aws_lambda_endpoints_sg_id
    )
    prefix_list_ids = [data.aws_vpc_endpoint.s3.prefix_list_id]
  }
}

#tfsec:ignore:aws-lambda-enable-tracing
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
      use_secrets_manager = var.config.use_secrets_manager
    }
  }

  dynamic "vpc_config" {
    for_each = var.config.vpc_enabled == true ? [var.config.vpc_enabled] : []
    content {
      subnet_ids         = var.config.subnet_ids
      security_group_ids = [aws_security_group.send_message_chunk[0].id]
    }
  }


  depends_on = [
    aws_cloudwatch_log_group.send_message_chunk,
    aws_iam_role_policy_attachment.send_message_chunk
  ]
}

resource "aws_cloudwatch_log_group" "send_message_chunk" {
  name              = "/aws/lambda/${local.send_message_chunk_name}"
  retention_in_days = var.cloudwatch_retention_in_days
  kms_key_id        = aws_kms_key.mesh.arn
}

resource "aws_iam_role" "send_message_chunk" {
  name               = "${local.send_message_chunk_name}-role"
  description        = "${local.send_message_chunk_name}-role"
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
  name        = "${local.send_message_chunk_name}-policy"
  description = "${local.send_message_chunk_name}-policy"
  policy      = data.aws_iam_policy_document.send_message_chunk.json
}

#tfsec:ignore:aws-iam-no-policy-wildcards
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
