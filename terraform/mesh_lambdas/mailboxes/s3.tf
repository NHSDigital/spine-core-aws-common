resource "aws_s3_bucket_object" "inbound" {
  bucket       = var.bucket_id
  key          = "inbound/${var.mailbox_id}/"
  acl          = "private"
  content_type = "application/x-directory"
}

# resource "aws_s3_bucket_object" "outbound" {
#   # var.mailbox.outbound_mappings is list of object with 1 element
#   # The given "for_each" argument value is unsuitable: "for_each" supports maps and sets of strings, but you have provided a set containing type object.
#   for_each = toset(var.mailbox.outbound_mappings)

#   bucket       = var.bucket_id
#   key          = "${each.key}/"
#   acl          = "private"
#   content_type = "application/x-directory"
# }
