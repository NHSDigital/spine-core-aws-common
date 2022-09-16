resource "aws_cloudwatch_event_rule" "get_messages_handshake" {
  name                = "${local.name}-get-messages-handshake"
  description         = "${local.name}-get-messages-handshake"
  schedule_expression = "cron(0 1 * * ? *)"
}

resource "aws_cloudwatch_event_target" "get_messages_handshake" {
  for_each = var.mailbox_ids

  rule      = aws_cloudwatch_event_rule.get_messages_handshake.name
  target_id = "GetMessages${each.key}"
  arn       = aws_sfn_state_machine.get_messages.arn
  role_arn  = aws_iam_role.get_messages_handshake_event.arn

  input = jsonencode({
    mailbox = each.value
    handshake = "true"
  })
}

resource "aws_iam_role" "get_messages_handshake_event" {
  name               = "${local.name}-get-messages-handshake-event"
  description        = "${local.name}-get-messages-handshake-event"
  assume_role_policy = data.aws_iam_policy_document.get_messages_handshake_event_assume.json
}

data "aws_iam_policy_document" "get_messages_handshake_event_assume" {
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

resource "aws_iam_role_policy_attachment" "get_messages_handshake_event" {
  role       = aws_iam_role.get_messages_handshake_event.name
  policy_arn = aws_iam_policy.get_messages_handshake_event.arn
}

resource "aws_iam_policy" "get_messages_handshake_event" {
  name        = "${local.name}-get-messages-handshake-event"
  description = "${local.name}-get-messages-handshake-event"
  policy      = data.aws_iam_policy_document.get_messages_handshake_event.json
}

data "aws_iam_policy_document" "get_messages_handshake_event" {
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
