resource "aws_cloudwatch_event_rule" "get_messages" {
  name                = "${local.name}-get-messages"
  description         = "${local.name}-get-messages"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "get_messages" {
  rule      = aws_cloudwatch_event_rule.get_messages.name
  target_id = "GetMessages"
  arn       = aws_sfn_state_machine.get_messages.arn
  role_arn  = aws_iam_role.get_messages_event.arn

  # TODO need this to come from list of mailboxes
  input = jsonencode({
    mailbox = "X26OT179"
  })
}

resource "aws_iam_role" "get_messages_event" {
  name               = "${local.name}-get-messages-event"
  description        = "${local.name}-get-messages-event"
  assume_role_policy = data.aws_iam_policy_document.get_messages_event_assume.json
}

data "aws_iam_policy_document" "get_messages_event_assume" {
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

resource "aws_iam_role_policy_attachment" "get_messages_event" {
  role       = aws_iam_role.get_messages_event.name
  policy_arn = aws_iam_policy.get_messages_event.arn
}

resource "aws_iam_policy" "get_messages_event" {
  name        = "${local.name}-get-messages-event"
  description = "${local.name}-get-messages-event"
  policy      = data.aws_iam_policy_document.get_messages_event.json
}

data "aws_iam_policy_document" "get_messages_event" {
  statement {
    sid    = "StepFunctionAllow"
    effect = "Allow"

    actions = [
      "states:StartExecution"
    ]

    resources = [
      aws_sfn_state_machine.get_messages.arn,
    ]
  }
}
