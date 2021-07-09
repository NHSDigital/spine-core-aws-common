# TODO
output "mailbox" {
  value = {
    inbound  = aws_s3_bucket_object.inbound[*]
    outbound = aws_s3_bucket_object.outbound[*]
  }
}
