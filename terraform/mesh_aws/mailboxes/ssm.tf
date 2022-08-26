resource "aws_ssm_parameter" "mailbox_allowed_senders" {
  # SSM does not support empty parameters
  count = var.mailbox.allowed_senders != null ? 1 : 0

  name      = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/ALLOWED_SENDERS"
  overwrite = true
  type      = "String"
  value     = var.mailbox.allowed_senders
}

resource "aws_ssm_parameter" "mailbox_allowed_recipients" {
  # SSM does not support empty parameters
  count = var.mailbox.allowed_recipients != null ? 1 : 0

  name      = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/ALLOWED_RECIPIENTS"
  overwrite = true
  type      = "String"
  value     = var.mailbox.allowed_recipients
}

resource "aws_ssm_parameter" "mailbox_allowed_workflow_ids" {
  # SSM does not support empty parameters
  count = var.mailbox.allowed_workflow_ids != null ? 1 : 0

  name      = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/ALLOWED_WORKFLOW_IDS"
  overwrite = true
  type      = "String"
  value     = var.mailbox.allowed_workflow_ids
}

resource "aws_ssm_parameter" "mailbox_password" {
  count = var.config.use_secrets_manager == "false" ? 1 : 0
  name      = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/MAILBOX_PASSWORD"
  type      = "SecureString"
  value     = "To Replace"
  overwrite = false

  lifecycle {
    ignore_changes = [
      value,
    ]
  }
}

resource "aws_secretsmanager_secret" "mailbox_password" {
  count = var.config.use_secrets_manager == "true" ? 1 : 0
  name      = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/MAILBOX_PASSWORD"
  description = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/MAILBOX_PASSWORD"
  kms_key_id  = var.key_id
}

resource "aws_ssm_parameter" "mailbox_inbound_bucket" {
  name      = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/INBOUND_BUCKET"
  overwrite = true
  type      = "String"
  value     = var.bucket_id
}

resource "aws_ssm_parameter" "mailbox_inbound_folder" {
  name      = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/INBOUND_FOLDER"
  overwrite = true
  type      = "String"
  # trim the trailing slash from the key, to stop double slash in the lambda output
  value = replace(aws_s3_bucket_object.inbound.key, "/", "")
}

# src_mailbox will always be the id of the parent mailbox variable
resource "aws_ssm_parameter" "outbound_mappings_src_mailbox" {
  for_each = { for outbound_mapping in var.mailbox.outbound_mappings : var.mailbox_id => outbound_mapping }

  name      = "/${var.name}/mesh/mapping/${var.bucket_id}/${replace(aws_s3_bucket_object.outbound[each.key].key, "/", "")}/src_mailbox"
  overwrite = true
  type      = "String"
  value     = var.mailbox_id
}

resource "aws_ssm_parameter" "outbound_mappings_dest_mailbox" {
  for_each = { for outbound_mapping in var.mailbox.outbound_mappings : var.mailbox_id => outbound_mapping }

  # Trim the slash off the end of the S3 key, so we don't end up with a double slash in the path
  name      = "/${var.name}/mesh/mapping/${var.bucket_id}/${replace(aws_s3_bucket_object.outbound[each.key].key, "/", "")}/dest_mailbox"
  overwrite = true
  type      = "String"
  value     = each.value.dest_mailbox
}

resource "aws_ssm_parameter" "outbound_mappings_workflow_id" {
  for_each = { for outbound_mapping in var.mailbox.outbound_mappings : var.mailbox_id => outbound_mapping }

  # Trim the slash off the end of the S3 key, so we don't end up with a double slash in the path
  name      = "/${var.name}/mesh/mapping/${var.bucket_id}/${replace(aws_s3_bucket_object.outbound[each.key].key, "/", "")}/workflow_id"
  overwrite = true
  type      = "String"
  value     = each.value.workflow_id
}
