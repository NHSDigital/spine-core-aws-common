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
        kms_master_key_id = aws_kms_key.mesh.key_id
        sse_algorithm     = "aws:kms"
      }
    }
  }

  versioning {
    enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "mesh" {
  bucket = aws_s3_bucket.mesh.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "mesh_bucket_policy" {
  bucket = aws_s3_bucket.mesh.id
  policy = data.aws_iam_policy_document.mesh_bucket_policy.json
}

data "aws_iam_policy_document" "mesh_bucket_policy" {
  statement {
    sid = "AllowSSLRequestsOnly"
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    resources = [
      "arn:aws:s3:::${local.name}",
      "arn:aws:s3:::${local.name}/*",
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
    effect = "Deny"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions = [
      "s3:*",
    ]
    resources = [
      "arn:aws:s3:::${local.name}",
      "arn:aws:s3:::${local.name}/*",
    ]
    condition {
      test = "NumericLessThan"
      values = [
        1.2,
      ]

      variable = "s3:TlsVersion"
    }
  }
}
