output "key" {
  value = {
    id    = aws_kms_key.key.key_id
    alias = aws_kms_alias.key.name
    arn   = aws_kms_key.key.arn
  }
}
