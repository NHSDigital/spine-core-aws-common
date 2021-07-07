resource "aws_sfn_state_machine" "send_message" {
  name     = "${local.name}-send-message"
  role_arn = aws_iam_role.send_message.arn

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.send_message.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  definition = jsonencode({
    Comment = "This is your state machine"
    StartAt = "Poll for messages"
    States = {
      "For each waiting message" = {
        ItemsPath = "$.body.messageList"
        Iterator = {
          StartAt = "Get and store message chunk"
          States = {
            "File complete" = {
              Type = "Succeed"
            }
            "Get and store message chunk" = {
              "Next"     = "Is this the last chunk?"
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
                  "MaxAttempts"   = 6
                },
              ]
              Type = "Task"
            }
            "Is this the last chunk?" = {
              Choices = [
                {
                  BooleanEquals = true
                  "Next"        = "File complete"
                  "Variable"    = "$.body.isLastChunk"
                },
              ]
              Default = "Get and store message chunk"
              "Type"  = "Choice"
            }
          }
        }
        MaxConcurrency = 1
        "Next"         = "Were there exactly 500 messages?"
        "ResultPath"   = null
        "Type"         = "Map"
      }
      "Poll complete " = {
        Type = "Succeed"
      }
      "Poll for messages" = {
        "Next"     = "For each waiting message"
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
            "MaxAttempts"   = 6
          },
        ]
        Type = "Task"
      }
      "Were there exactly 500 messages?" = {
        Choices = [
          {
            "Next"        = "Poll for messages"
            NumericEquals = 500
            "Variable"    = "$.body.messageCount"
          },
        ]
        Default = "Poll complete"
        "Type"  = "Choice"
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
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.send_message.arn}*"
    ]
  }

  statement {
    sid    = "LamdaInvokeAllow"
    effect = "Allow"

    resources = [
      aws_lambda_function.send_message_chunk.arn,
      aws_lambda_function.check_send_parameters.arn
    ]

    actions = ["lambda:InvokeFunction"]
  }
}
