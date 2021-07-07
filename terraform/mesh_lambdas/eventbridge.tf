resource "aws_cloudwatch_event_rule" "get_messages" {
  name                = "${local.name}-get-messages"
  description         = "${local.name}-get-messages"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "get_messages" {
  rule      = aws_cloudwatch_event_rule.get_messages.name
  target_id = "GetMessages"
  input     = "{\"mailbox\": \"X26OT179\"}"
  arn       = aws_sfn_state_machine.get_messages.arn
}

resource "aws_cloudwatch_event_rule" "send_message" {
  name          = "${local.name}-send-messages"
  description   = "${local.name}-send-messages"
  event_pattern = jsonencode(local.send_message_event_pattern)
}

resource "aws_cloudwatch_event_target" "send_message" {
  rule      = aws_cloudwatch_event_rule.send_message.name
  target_id = "SendMessage"
  # TODO need this to come from list of mailboxes
  input = jsonencode(local.send_message_input)
  arn   = aws_sfn_state_machine.send_message.arn
}

locals {
  # TODO need this to come from list of mailboxes
  send_message_input = {
    mailbox = "X26OT179"
  }

  send_message_event_pattern = {
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
      }
    }
  }
}
