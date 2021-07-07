resource "aws_lambda_function" "check_send_parameters" {
  function_name    = "${local.name}-check-send-parameters"
  filename         = data.archive_file.mesh_implementation_lambdas.output_path
  handler          = "mesh_check_send_parameters_application_lambda.lambda_handler"
  runtime          = local.python_runtime
  timeout          = local.lambda_timeout
  source_code_hash = data.archive_file.mesh_implementation_lambdas.output_base64sha256
  role             = aws_iam_role.check_send_parameters.arn
  layers           = [aws_lambda_layer_version.mesh_implementation_lambdas_dependencies.arn]

  environment {
    variables = {
      ENV = local.name
    }
  }

  depends_on = [aws_cloudwatch_log_group.check_send_parameters]
}

resource "aws_cloudwatch_log_group" "check_send_parameters" {
  name              = "/aws/lambda/${local.name}-check-send-parameters"
  retention_in_days = 365
}

resource "aws_iam_role" "check_send_parameters" {
  name               = "${local.name}-check_send_parameters"
  description        = "${local.name}-check_send_parameters"
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
  name        = "${local.name}-check_send_parameters"
  description = "${local.name}-check_send_parameters"
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
      "${aws_cloudwatch_log_group.check_send_parameters.arn}*"
    ]
  }
}

# {
#     "Version": "2012-10-17",
#     "Statement": [
#         {
#             "Effect": "Allow",
#             "Action": [
#                 "logs:CreateLogStream",
#                 "logs:PutLogEvents"
#             ],
#             "Resource": [
#                 "arn:aws:logs:eu-west-2:092420156801:log-group:/aws/lambda/meshtest2-mesh-check-send-parameters:*",
#                 "arn:aws:logs:eu-west-2:092420156801:log-group:/aws/vendedlogs/states/meshtest2-mesh-get-messages-Logs:*"
#             ]
#         },
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
#             "Resource": [
#                 "arn:aws:kms:eu-west-2:092420156801:key/dd6c0abc-30e6-4c37-8f86-8cf1ca6c2f00",
#                 "arn:aws:kms:eu-west-2:092420156801:key/4f295c4c-17fd-4c9d-84e9-266b01de0a5a"
#             ]
#         },
#         {
#             "Effect": "Allow",
#             "Action": "states:ListStateMachines",
#             "Resource": "arn:aws:states:eu-west-2:092420156801:stateMachine:*"
#         },
#         {
#             "Effect": "Allow",
#             "Action": [
#                 "states:ListExecutions",
#                 "states:DescribeExecution"
#             ],
#             "Resource": [
#                 "arn:aws:states:eu-west-2:092420156801:stateMachine:meshtest2-*"
#             ]
#         },
#         {
#             "Effect": "Allow",
#             "Action": [
#                 "s3:GetObject",
#                 "s3:ListBucket"
#             ],
#             "Resource": [
#                 "arn:aws:s3:::meshtest2-*"
#             ]
#         }
#     ]
# }
