module "mailboxes" {
  for_each = { for mailbox in var.mailboxes : mailbox.id => mailbox }

  source = "./mailboxes"

  name       = local.name
  bucket_id  = aws_s3_bucket.mesh.id
  mailbox_id = each.key
  mailbox    = each.value
}
