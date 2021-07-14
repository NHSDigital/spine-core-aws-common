output "mailbox" {
  value = {
    bucket   = var.bucket_id
    inbound  = aws_s3_bucket_object.inbound[*].key
    outbound = [for o in aws_s3_bucket_object.outbound : o.key]
  }
}
