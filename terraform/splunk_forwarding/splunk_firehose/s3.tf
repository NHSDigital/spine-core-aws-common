resource "aws_s3_bucket" "splunk_firehose" {
  bucket = "${local.name}-backup"
  acl    = "private"

  # TODO must be KMS
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  versioning {
    enabled = true
  }
}
