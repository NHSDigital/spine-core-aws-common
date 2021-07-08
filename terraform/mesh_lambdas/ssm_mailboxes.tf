# resource "aws_ssm_parameter" "mailbox_allowed_senders" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name  = "/${local.name}/mesh/mailboxes/${each.value.id}/ALLOWED_SENDERS"
#   type  = "String"
#   value = each.value.allowed_senders
# }

# resource "aws_ssm_parameter" "mailbox_allowed_recipients" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name  = "/${local.name}/mesh/mailboxes/${each.value.id}/ALLOWED_RECIPIENTS"
#   type  = "String"
#   value = each.value.allowed_recipients
# }

# resource "aws_ssm_parameter" "mailbox_allowed_workflow_ids" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name  = "/${local.name}/mesh/mailboxes/${each.value.id}/ALLOWED_WORKFLOW_IDS"
#   type  = "String"
#   value = each.value.allowed_workflow_ids
# }

# resource "aws_ssm_parameter" "mailbox_password" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name  = "/${local.name}/mesh/mailboxes/${each.value.id}/MAILBOX_PASSWORD"
#   type  = "SecureString"
#   value = each.value.password
# }

# resource "aws_ssm_parameter" "mailbox_inbound_bucket" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name  = "/${local.name}/mesh/mailboxes/${each.value.id}/INBOUND_BUCKET"
#   type  = "String"
#   value = each.value.inbound_bucket
# }

# resource "aws_ssm_parameter" "mailbox_inbound_folder" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name  = "/${local.name}/mesh/mailboxes/${each.value.id}/INBOUND_FOLDER"
#   type  = "String"
#   value = each.value.inbound_folder
# }

# resource "aws_ssm_parameter" "outbound_mappings_src_mailbox" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name = "/${local.name}/mesh/mapping/test/test/src_mailbox"
#   # TODO lookup bucket/folder from mailbox mapping s3 object
#   # name  = "/${local.name}/mesh/mapping/${each.value.bucket}/${each.value.folder}/src_mailbox"
#   type  = "String"
#   value = "TBC"
# }

# resource "aws_ssm_parameter" "outbound_mappings_dest_mailbox" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name  = "/${local.name}/mesh/mapping/${each.value.bucket}/${each.value.folder}/dest_mailbox"
#   type  = "String"
#   value = "TBC"
# }

# resource "aws_ssm_parameter" "outbound_mappings_workflow_id" {
#   for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

#   name  = "/${local.name}/mesh/mapping/${each.value.bucket}/${each.value.folder}/workflow_id"
#   type  = "String"
#   value = "TBC"
# }
