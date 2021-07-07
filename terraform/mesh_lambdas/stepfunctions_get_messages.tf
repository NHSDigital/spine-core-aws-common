resource "aws_sfn_state_machine" "get_messages" {
  name     = "${local.name}-get-messages"
  role_arn = aws_iam_role.get_messages.arn

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.get_messages.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  definition = jsonencode({
    Comment = "meshtest2-mesh-send-message"
    StartAt = "Check send parameters"
    States = {
      "Check send parameters" = {
        Next       = "Send message chunk"
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
      Choice = {
        Choices = [
          {
            BooleanEquals = false
            Next          = "Send message chunk"
            Variable      = "$.body.isLastChunk"
          },
        ]
        Default = "Success"
        Type    = "Choice"
      }
      "Send message chunk" = {
        Next       = "Choice"
        OutputPath = "$.Payload"
        Parameters = {
          FunctionName = "${aws_lambda_function.fetch_message_chunk.arn}:$LATEST"
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

resource "aws_cloudwatch_log_group" "get_messages" {
  name              = "/aws/states/${local.name}-get-messages"
  retention_in_days = 365
}

resource "aws_iam_role" "get_messages" {
  name               = "${local.name}-get-messages"
  description        = "${local.name}-get-messages"
  assume_role_policy = data.aws_iam_policy_document.get_messages_assume.json
}

data "aws_iam_policy_document" "get_messages_assume" {
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

resource "aws_iam_role_policy_attachment" "get_messages" {
  role       = aws_iam_role.get_messages.name
  policy_arn = aws_iam_policy.get_messages.arn
}

resource "aws_iam_policy" "get_messages" {
  name        = "${local.name}-get-messages"
  description = "${local.name}-get-messages"
  policy      = data.aws_iam_policy_document.get_messages.json
}

data "aws_iam_policy_document" "get_messages" {
  statement {
    sid    = "CloudWatchAllow"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.get_messages.arn}*"
    ]
  }

  statement {
    sid    = "LamdaInvokeAllow"
    effect = "Allow"

    resources = [
      aws_lambda_function.fetch_message_chunk.arn,
      aws_lambda_function.check_send_parameters.arn
    ]

    actions = ["lambda:InvokeFunction"]
  }
}
