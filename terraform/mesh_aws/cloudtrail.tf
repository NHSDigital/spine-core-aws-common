resource "aws_cloudtrail" "s3logs" {
  count                         = var.config.create_s3logs_cloudtrail ? 1 : 0
  name                          = "${local.name}-s3logs"
  s3_bucket_name                = aws_s3_bucket.s3logs.id
  s3_key_prefix                 = "AWSLogs"
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  kms_key_id                    = aws_kms_key.mesh.arn
  cloud_watch_logs_group_arn    = "${aws_cloudwatch_log_group.mesh_cloudtrail.arn}:*"
  cloud_watch_logs_role_arn     = aws_iam_role.mesh_cloudtrail_to_cloudwatch_role.arn

  event_selector {
    read_write_type           = "WriteOnly"
    include_management_events = false

    data_resource {
      type = "AWS::S3::Object"
      values = [
        "${aws_s3_bucket.mesh.arn}/"
      ]
    }
  }
}

resource "aws_cloudwatch_log_group" "mesh_cloudtrail" {
  count             = var.config.create_s3logs_cloudtrail ? 1 : 0
  name              = "/aws/cloudtrail/mesh-s3-logs"
  retention_in_days = var.mesh_cloudwatch_log_retention_in_days
  kms_key_id        = aws_kms_key.mesh.arn
}

resource "aws_iam_role" "mesh_cloudtrail_to_cloudwatch_role" {
  count              = var.config.create_s3logs_cloudtrail ? 1 : 0
  name               = "cloudtrail-cloudwatch-mesh-role"
  description        = "cloudtrail-cloudwatch-mesh-role"
  assume_role_policy = data.aws_iam_policy_document.role_assume.json
}

resource "aws_iam_role_policy_attachment" "policy_attachment" {
  count      = var.config.create_s3logs_cloudtrail ? 1 : 0
  role       = aws_iam_role.mesh_cloudtrail_to_cloudwatch_role.name
  policy_arn = aws_iam_policy.mesh_cloudtrail_cloudwatch_policy.arn
}

resource "aws_iam_policy" "mesh_cloudtrail_cloudwatch_policy" {
  count       = var.config.create_s3logs_cloudtrail ? 1 : 0
  name        = "mesh-cloudtrail-cloudwatch-policy"
  description = "mesh-cloudtrail-cloudwatch-policy"
  policy      = data.aws_iam_policy_document.mesh_cloudtrail_policy.json
}


data "aws_iam_policy_document" "role_assume" {
  count  = var.config.create_s3logs_cloudtrail ? 1 : 0
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"

      identifiers = [
        "cloudtrail.amazonaws.com",
      ]
    }
  }
}

#tfsec:ignore:aws-iam-no-policy-wildcards
data "aws_iam_policy_document" "mesh_cloudtrail_policy" {
  count  = var.config.create_s3logs_cloudtrail ? 1 : 0
  statement {
    sid    = "MeshAllowAccessToLogsService"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      aws_cloudwatch_log_group.mesh_cloudtrail.arn,
      "${aws_cloudwatch_log_group.mesh_cloudtrail.arn}:*"
    ]
  }
  statement {
    sid    = "MeshAllowAccessToMeshCloudtrailS3Bucket"
    effect = "Allow"

    actions = [
      "s3:*",
    ]

    resources = [
      aws_s3_bucket.mesh.arn,
      "${aws_s3_bucket.mesh.arn}/AWSLogs/*"
    ]
  }
  statement {
    sid    = "MeshAllowAccessToMeshKMSKey"
    effect = "Allow"

    actions = [
      "kms:*",
    ]

    resources = [
      aws_kms_key.mesh.arn
    ]
  }
}
