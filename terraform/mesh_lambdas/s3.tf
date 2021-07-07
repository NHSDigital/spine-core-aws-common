resource "aws_s3_bucket" "mesh" {
  bucket = local.name
  acl    = "private"

  # TODO up to KMS encryption
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
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

# TODO AWS CloudTrail object level logging
# meshtest2-S3Event

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

# TODO get from passed in mapping
# resource "aws_s3_bucket_object" "outbound" {
#   for_each = []

#   bucket       = aws_s3_bucket.mesh.id
#   key          = "${each.key}/"
#   acl          = "private"
#   content_type = "application/x-directory"
# }

# resource "aws_s3_bucket_notification" "lambda_triggers" {
#   bucket = aws_s3_bucket.mesh.id

#   lambda_function {
#     lambda_function_arn = aws_lambda_function.example.arn
#     events              = ["s3:ObjectCreated:*"]
#     filter_prefix       = "outbound/"
#   }

#   depends_on = [
#     aws_lambda_permission.example,
#   ]
# }
