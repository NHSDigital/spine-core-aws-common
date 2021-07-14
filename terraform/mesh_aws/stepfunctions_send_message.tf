resource "aws_sfn_state_machine" "send_message" {
  name     = "${local.name}-send-message"
  type     = "STANDARD"
  role_arn = aws_iam_role.send_message.arn

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.send_message.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  definition = jsonencode({
    Comment = "${local.name}-send-message"
    StartAt = "Check send parameters"
    States = {
      "Check send parameters" = {
        Next       = "Failed?"
        OutputPath = "$.Payload"
        Parameters = {
          FunctionName = "${aws_lambda_function.check_send_parameters.arn}:$LATEST"
          "Payload.$"  = "$"
        }
        Resource = "arn:aws:states:::lambda:invoke"
        Retry = [
          {
            BackoffRate = 2
            ErrorEquals = [
              "Lambda.ServiceException",
              "Lambda.AWSLambdaException",
              "Lambda.SdkClientException",
            ]
            IntervalSeconds = 2
            MaxAttempts     = 6
          },
        ]
        Type = "Task"
      }
      "Completed sending?" = {
        Choices = [
          {
            BooleanEquals = true
            Next          = "Success"
            Variable      = "$.body.complete"
          },
        ]
        Default = "Send message chunk"
        Type    = "Choice"
      }
      Fail = {
        Type = "Fail"
      }
      "Failed?" = {
        Choices = [
          {
            Next                     = "Fail"
            NumericGreaterThanEquals = 300
            Variable                 = "$.statusCode"
          },
        ]
        Default = "Send message chunk"
        Type    = "Choice"
      }
      "Send message chunk" = {
        Next       = "Completed sending?"
        OutputPath = "$.Payload"
        Parameters = {
          FunctionName = "${aws_lambda_function.send_message_chunk.arn}:$LATEST"
          "Payload.$"  = "$"
        }
        Resource = "arn:aws:states:::lambda:invoke"
        Retry = [
          {
            BackoffRate = 2
            ErrorEquals = [
              "Lambda.ServiceException",
              "Lambda.AWSLambdaException",
              "Lambda.SdkClientException",
            ]
            IntervalSeconds = 2
            MaxAttempts     = 6
          },
        ]
        Type = "Task"
      }
      Success = {
        Type = "Succeed"
      }
    }
  })
}

resource "aws_cloudwatch_log_group" "send_message" {
  name              = "/aws/states/${local.name}-send-message"
  retention_in_days = 365
}

resource "aws_iam_role" "send_message" {
  name               = "${local.name}-send-message"
  description        = "${local.name}-send-message"
  assume_role_policy = data.aws_iam_policy_document.send_message_assume.json
}

data "aws_iam_policy_document" "send_message_assume" {
  statement {
    actions = [
      "sts:AssumeRole"
    ]

    principals {
      type = "Service"

      identifiers = [
        "states.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role_policy_attachment" "send_message" {
  role       = aws_iam_role.send_message.name
  policy_arn = aws_iam_policy.send_message.arn
}

resource "aws_iam_policy" "send_message" {
  name        = "${local.name}-send-message"
  description = "${local.name}-send-message"
  policy      = data.aws_iam_policy_document.send_message.json
}

data "aws_iam_policy_document" "send_message" {
  statement {
    sid    = "CloudWatchAllow"
    effect = "Allow"

    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups"
    ]

    # AWS Bug creating a policy too large if you use anything but "*" here
    # resulting in a failed terraform deployment
    # https://forums.aws.amazon.com/thread.jspa?threadID=321488
    resources = ["*"]
  }

  statement {
    sid    = "LamdaInvokeAllow"
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction"
    ]

    resources = [
      aws_lambda_function.send_message_chunk.arn,
      "${aws_lambda_function.send_message_chunk.arn}:*",
      aws_lambda_function.check_send_parameters.arn,
      "${aws_lambda_function.check_send_parameters.arn}:*"
    ]
  }
}
