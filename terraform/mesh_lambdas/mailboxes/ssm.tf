resource "aws_ssm_parameter" "mailbox_allowed_senders" {
  # SSM does not support empty parameters
  count = var.mailbox.allowed_senders != null ? 1 : 0

  name  = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/ALLOWED_SENDERS"
  type  = "String"
  value = var.mailbox.allowed_senders
}

resource "aws_ssm_parameter" "mailbox_allowed_recipients" {
  # SSM does not support empty parameters
  count = var.mailbox.allowed_recipients != null ? 1 : 0

  name  = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/ALLOWED_RECIPIENTS"
  type  = "String"
  value = var.mailbox.allowed_recipients
}

resource "aws_ssm_parameter" "mailbox_allowed_workflow_ids" {
  # SSM does not support empty parameters
  count = var.mailbox.allowed_workflow_ids != null ? 1 : 0

  name  = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/ALLOWED_WORKFLOW_IDS"
  type  = "String"
  value = var.mailbox.allowed_workflow_ids
}

resource "aws_ssm_parameter" "mailbox_password" {
  name  = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/MAILBOX_PASSWORD"
  type  = "SecureString"
  value = "To Replace"

  lifecycle {
    ignore_changes = [
      value
    ]
  }
}

resource "aws_ssm_parameter" "mailbox_inbound_bucket" {
  name  = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/INBOUND_BUCKET"
  type  = "String"
  value = var.bucket_id
}

resource "aws_ssm_parameter" "mailbox_inbound_folder" {
  name  = "/${var.name}/mesh/mailboxes/${var.mailbox_id}/INBOUND_FOLDER"
  type  = "String"
  value = aws_s3_bucket_object.inbound.key
}

# resource "aws_ssm_parameter" "outbound_mappings_src_mailbox" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name = "/${var.name}/mesh/mapping/test/test/src_mailbox"
#   # TODO lookup bucket/folder from mailbox mapping s3 object
#   # name  = "/${var.name}/mesh/mapping/${each.value.bucket}/${each.value.folder}/src_mailbox"
#   type  = "String"
#   value = "TBC"
# }

# resource "aws_ssm_parameter" "outbound_mappings_dest_mailbox" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name  = "/${var.name}/mesh/mapping/${each.value.bucket}/${each.value.folder}/dest_mailbox"
#   type  = "String"
#   value = "TBC"
# }

# resource "aws_ssm_parameter" "outbound_mappings_workflow_id" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name  = "/${var.name}/mesh/mapping/${each.value.bucket}/${each.value.folder}/workflow_id"
#   type  = "String"
#   value = "TBC"
# }
