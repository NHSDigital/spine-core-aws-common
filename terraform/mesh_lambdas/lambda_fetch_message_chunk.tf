resource "aws_lambda_function" "fetch_message_chunk" {
  function_name    = "${local.name}-fetch-message-chunk"
  filename         = data.archive_file.mesh_implementation_lambdas.output_path
  handler          = "mesh_fetch_message_chunk_application_lambda.lambda_handler"
  runtime          = local.python_runtime
  timeout          = local.lambda_timeout
  source_code_hash = data.archive_file.mesh_implementation_lambdas.output_base64sha256
  role             = aws_iam_role.fetch_message_chunk.arn
  layers           = [aws_lambda_layer_version.mesh_implementation_lambdas_dependencies.arn]

  environment {
    variables = {
      ENV = local.name
    }
  }

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

# {
#     "Version": "2012-10-17",
#     "Statement": [
#         {
#             "Effect": "Allow",
#             "Action": [
#                 "ssm:DescribeParameters"
#             ],
#             "Resource": "*"
#         },
#         {
#             "Effect": "Allow",
#             "Action": [
#                 "ssm:GetParametersByPath"
#             ],
#             "Resource": [
#                 "arn:aws:ssm:eu-west-2:092420156801:parameter/meshtest2/*",
#                 "arn:aws:ssm:eu-west-2:092420156801:parameter/meshtest2"
#             ]
#         },
#         {
#             "Effect": "Allow",
#             "Action": "kms:Decrypt",
#             "Resource": "arn:aws:kms:eu-west-2:092420156801:key/dd6c0abc-30e6-4c37-8f86-8cf1ca6c2f00"
#         },
#         {
#             "Effect": "Allow",
#             "Action": [
#                 "kms:Encrypt",
#                 "kms:GenerateDataKey*"
#             ],
#             "Resource": "arn:aws:kms:eu-west-2:092420156801:key/4f295c4c-17fd-4c9d-84e9-266b01de0a5a"
#         },
#         {
#             "Effect": "Allow",
#             "Action": [
#                 "s3:PutObject",
#                 "s3:AbortMultipartUpload"
#             ],
#             "Resource": "arn:aws:s3:::meshtest2-*"
#         }
#     ]
# }
