resource "aws_cloudwatch_log_subscription_filter" "splunk_forwarding" {
  for_each = toset(var.cloudwatch_log_groups_to_forward)

  name            = local.name
  role_arn        = aws_iam_role.cloudwatch_subscription.arn
  destination_arn = var.splunk_firehose.arn
  log_group_name  = each.value
  filter_pattern  = "" # don't filter any logs

  depends_on = [
    aws_iam_role_policy_attachment.cloudwatch_subscription,
  ]
}
