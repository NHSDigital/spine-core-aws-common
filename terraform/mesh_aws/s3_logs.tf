#tfsec:ignore:aws-cloudtrail-require-bucket-access-logging tfsec:ignore:aws-s3-enable-versioning
resource "aws_s3_bucket" "s3logs" {
  bucket = "${local.name}-s3logs"

  lifecycle_rule {
    id      = "AWSLogs"
    enabled = true
    prefix  = "AWSLogs/"

    expiration {
      days = var.s3logs_retention_in_days
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3logs_encryption_configuration" {
  bucket = aws_s3_bucket.s3logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "s3logs" {
  bucket = aws_s3_bucket.s3logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "s3logs_controls" {
  bucket = aws_s3_bucket.s3logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "s3logs_acl" {
  depends_on = [aws_s3_bucket_ownership_controls.s3logs_controls]

  bucket = aws_s3_bucket.s3logs.id
  acl    = "log-delivery-write"
}

resource "aws_s3_bucket_policy" "s3logs_policy" {
  bucket = aws_s3_bucket.s3logs.id
  policy = data.aws_iam_policy_document.s3logs.json
}

data "aws_iam_policy_document" "s3logs" {
  statement {
    sid = "AllowSSLRequestsOnly"
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    resources = [
      "arn:aws:s3:::${local.name}-s3logs",
      "arn:aws:s3:::${local.name}-s3logs/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test = "Bool"
      values = [
        "false",
      ]

      variable = "aws:SecureTransport"
    }
  }
  statement {
    sid    = "AWSCloudTrailAclCheck"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }

    actions = [
      "s3:GetBucketAcl"
    ]

    resources = [
      "arn:aws:s3:::${local.name}-s3logs"
    ]
  }

  statement {
    sid    = "AWSCloudTrailWrite"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }

    actions = [
      "s3:PutObject"
    ]

    resources = [
      "arn:aws:s3:::${local.name}-s3logs/AWSLogs/*"
    ]

    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
}
