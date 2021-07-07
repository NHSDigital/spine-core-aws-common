resource "aws_ssm_parameter" "outbound_mappings_src_mailbox" {
  for_each = { for mapping in var.outbound_mappings : mapping.src_mailbox => mapping }

  name = "/${local.name}/mesh/mapping/test/test/src_mailbox"
  # TODO lookup bucket/folder from mailbox mapping s3 object
  # name  = "/${local.name}/mesh/mapping/${each.value.bucket}/${each.value.folder}/src_mailbox"
  type  = "String"
  value = each.value.src_mailbox
}

resource "aws_ssm_parameter" "outbound_mappings_dest_mailbox" {
  for_each = { for mapping in var.outbound_mappings : mapping.folder => mapping }

  name  = "/${local.name}/mesh/mapping/${each.value.bucket}/${each.value.folder}/dest_mailbox"
  type  = "String"
  value = each.value.dest_mailbox
}

resource "aws_ssm_parameter" "outbound_mappings_workflow_id" {
  for_each = { for mapping in var.outbound_mappings : mapping.folder => mapping }

  name  = "/${local.name}/mesh/mapping/${each.value.bucket}/${each.value.folder}/workflow_id"
  type  = "String"
  value = each.value.workflow_id
}
