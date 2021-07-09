resource "aws_cloudwatch_event_rule" "send_message_event" {
  name        = "${local.name}-send-messages"
  description = "${local.name}-send-messages"
  event_pattern = jsonencode({
    source = [
      "aws.s3"
    ]
    detail-type = [
      "AWS API Call via CloudTrail"
    ]
    detail = {
      eventSource = [
        "s3.amazonaws.com"
      ]
      eventName = [
        "PutObject",
        "CompleteMultipartUpload"
      ]
      requestParameters = {
        bucketName = [
          aws_s3_bucket.mesh.id
        ]
        key = [
          {
            prefix = "outbound"
          }
        ]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "send_message_event" {
  rule      = aws_cloudwatch_event_rule.send_message_event.name
  target_id = "SendMessage"
  arn       = aws_sfn_state_machine.send_message.arn
  role_arn  = aws_iam_role.send_message_event.arn
}

resource "aws_iam_role" "send_message_event" {
  name               = "${local.name}-send-message-event"
  description        = "${local.name}-send-message-event"
  assume_role_policy = data.aws_iam_policy_document.send_message_event_assume.json
}

data "aws_iam_policy_document" "send_message_event_assume" {
  statement {
    actions = [
      "sts:AssumeRole"
    ]

    principals {
      type = "Service"

      identifiers = [
        "events.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role_policy_attachment" "send_message_event" {
  role       = aws_iam_role.send_message_event.name
  policy_arn = aws_iam_policy.send_message_event.arn
}

resource "aws_iam_policy" "send_message_event" {
  name        = "${local.name}-send-message-event"
  description = "${local.name}-send-message-event"
  policy      = data.aws_iam_policy_document.send_message_event.json
}

data "aws_iam_policy_document" "send_message_event" {
  statement {
    sid    = "StepFunctionAllow"
    effect = "Allow"

    actions = [
      "states:StartExecution"
    ]

    resources = [
      aws_sfn_state_machine.send_message.arn,
    ]
  }
}
