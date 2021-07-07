output "bucket" {
  value = {
    name = aws_s3_bucket.mesh.id
    arn  = aws_s3_bucket.mesh.arn
  }
}

output "config" {
  value = var.config
}

output "mailboxes" {
  value = var.mailboxes
}
