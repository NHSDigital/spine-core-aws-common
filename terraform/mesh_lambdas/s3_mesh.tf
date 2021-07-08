resource "aws_s3_bucket" "mesh" {
  bucket = local.name
  acl    = "private"

  logging {
    target_bucket = aws_s3_bucket.s3logs.id
    target_prefix = "bucket_logs/"
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.mesh.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }
}

resource "aws_s3_bucket_public_access_block" "mesh" {
  bucket = aws_s3_bucket.mesh.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_object" "folders" {
  for_each = toset([
    "inbound",
    "outbound",
  ])

  bucket       = aws_s3_bucket.mesh.id
  key          = "${each.key}/"
  acl          = "private"
  content_type = "application/x-directory"
}
