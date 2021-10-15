resource "aws_kinesis_firehose_delivery_stream" "splunk_kinesis_firehose" {
  name        = "${var.environment}-${var.project}-splunk-kinesis-firehose-to-splunk-stream"
  destination = "splunk"

  s3_configuration {
    role_arn           = aws_iam_role.splunk_kinesis_firehose.arn
    prefix             = "splunk-kinesis-firehose/"
    bucket_arn         = aws_s3_bucket.kinesis_firehose_s3_bucket.arn
    buffer_size        = 5
    buffer_interval    = 300
    compression_format = "GZIP"
  }

  splunk_configuration {
    hec_endpoint               = var.splunk_hec_endpoint
    hec_token                  = var.splunk_hec_token
    hec_acknowledgment_timeout = 300
    hec_endpoint_type          = "Event"
    s3_backup_mode             = "FailedEventsOnly"

    processing_configuration {
      enabled = "true"

      processors {
        type = "Lambda"

        parameters {
          parameter_name  = "LambdaArn"
          parameter_value = "${aws_lambda_function.splunk_formatter_lambda.arn}:$LATEST"
        }
        parameters {
          parameter_name  = "RoleArn"
          parameter_value = aws_iam_role.splunk_kinesis_firehose.arn
        }
      }
    }

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.splunk_kinesis_logs.name
      log_stream_name = aws_cloudwatch_log_stream.splunk_firehose_logs.name
    }
  }

  tags = merge(
    {
      "Name" = "${var.environment}-${var.project}-splunk-kinesis-firehose-to-splunk-stream"
    },
    var.common_tags,
  )
}

# S3 Bucket for Kinesis Firehose s3_backup_mode
resource "aws_s3_bucket" "kinesis_firehose_s3_bucket" {
  bucket = "${var.environment}-${var.project}-kinesis-backup-bucket"
  acl    = "private"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = merge(
    {
      "Name" = "${var.environment}-${var.project}-kinesis-backup-bucket"
    },
    var.common_tags,
  )

  versioning {
    enabled = true
  }
}

# Cloudwatch logging group for Kinesis Firehose
resource "aws_cloudwatch_log_group" "splunk_kinesis_logs" {
  name              = "/aws/kinesisfirehose/${var.environment}-${var.project}-splunk-firehose-logs"
  retention_in_days = 30
  kms_key_id        = var.kms_key_arn == "" ? null : var.kms_key_arn

  tags = merge(
    {
      "Name" = "${var.environment}-${var.project}-splunk-firehose-logs"
    },
    var.common_tags,
  )
}

# Create the stream
resource "aws_cloudwatch_log_stream" "splunk_firehose_logs" {
  name           = "${var.environment}-${var.project}-splunk-firehose-logs"
  log_group_name = aws_cloudwatch_log_group.splunk_kinesis_logs.name
}

# Role for the transformation Lambda function attached to the kinesis stream
resource "aws_iam_role" "splunk_formatter_lambda" {
  name        = "${var.environment}-${var.project}-splunk-formatter-lambda-role"
  description = "Role for Lambda function to transformation CloudWatch logs into Splunk compatible format"

  assume_role_policy = <<POLICY
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      }
    }
  ],
  "Version": "2012-10-17"
}
POLICY


  tags = merge(
    {
      "Name" = "${var.environment}-${var.project}-splunk-formatter-lambda-role"
    },
    var.common_tags,
  )
}

data "aws_iam_policy_document" "splunk_formatter_lambda_policy_doc" {
  statement {
    actions = [
      "logs:GetLogEvents",
      "logs:PutLogEvents",
      "logs:CreateLogStream",
    ]

    resources = [
      "*",
    ]

    effect = "Allow"
  }

  statement {
    actions = [
      "firehose:PutRecordBatch",
    ]

    resources = [
      aws_kinesis_firehose_delivery_stream.splunk_kinesis_firehose.arn
    ]
  }
}

resource "aws_iam_policy" "splunk_formatter_lambda_policy" {
  name   = "${var.environment}-${var.project}-splunk-formatter-lambda-policy"
  policy = data.aws_iam_policy_document.splunk_formatter_lambda_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "splunk_formatter_lambda_policy_role_attachment" {
  role       = aws_iam_role.splunk_formatter_lambda.name
  policy_arn = aws_iam_policy.splunk_formatter_lambda_policy.arn
}

data "archive_file" "splunk_formatter_lambda_archive" {
  type        = "zip"
  source_dir  = var.lambda_source_dir
  output_path = var.lambda_output_path
}

# Create the lambda function
# The lambda function to transform data from compressed format in Cloudwatch to something Splunk can handle (uncompressed)
resource "aws_lambda_function" "splunk_formatter_lambda" {
  function_name    = "${var.environment}-${var.project}-splunk-formatter-lambda"
  description      = "Transform data from CloudWatch format to Splunk event compatible format"
  filename         = data.archive_file.splunk_formatter_lambda_archive.output_path
  role             = aws_iam_role.splunk_formatter_lambda.arn
  handler          = var.lambda_handler
  source_code_hash = data.archive_file.splunk_formatter_lambda_archive.output_base64sha256
  runtime          = "python3.8"
  timeout          = 360
  memory_size      = var.lambda_memory

  environment {
    variables = var.lambda_env_vars == {} ? null : var.lambda_env_vars
  }
}

# Role for Kinesis Firehose
resource "aws_iam_role" "splunk_kinesis_firehose" {
  name        = "${var.environment}-${var.project}-splunk-kinesis-firehose-role"
  description = "IAM Role for Kinesis Firehose"

  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Principal": {
        "Service": "firehose.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Effect": "Allow"
    }
  ]
}
POLICY

}

data "aws_iam_policy_document" "splunk_kinesis_firehose_policy_document" {
  statement {
    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject",
    ]

    resources = [
      aws_s3_bucket.kinesis_firehose_s3_bucket.arn,
      "${aws_s3_bucket.kinesis_firehose_s3_bucket.arn}/*",
    ]

    effect = "Allow"
  }

  statement {
    actions = [
      "lambda:InvokeFunction",
      "lambda:GetFunctionConfiguration",
    ]

    resources = [
      "${aws_lambda_function.splunk_formatter_lambda.arn}:$LATEST",
    ]
  }

  statement {
    actions = [
      "logs:PutLogEvents",
    ]

    resources = [
      aws_cloudwatch_log_group.splunk_kinesis_logs.arn,
      aws_cloudwatch_log_stream.splunk_firehose_logs.arn
    ]

    effect = "Allow"
  }
}

resource "aws_iam_policy" "splunk_kinesis_firehose_iam_policy" {
  name   = "${var.environment}-${var.project}-splunk-kinesis-firehose-policy"
  policy = data.aws_iam_policy_document.splunk_kinesis_firehose_policy_document.json
}

resource "aws_iam_role_policy_attachment" "splunk_kinesis_fh_role_attachment" {
  role       = aws_iam_role.splunk_kinesis_firehose.name
  policy_arn = aws_iam_policy.splunk_kinesis_firehose_iam_policy.arn
}

# Cloudwatch logging group for Splunk Formatter Lambda
resource "aws_cloudwatch_log_group" "splunk_formatter_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.splunk_formatter_lambda.function_name}"
  retention_in_days = 30
  kms_key_id        = var.kms_key_arn == "" ? null : var.kms_key_arn

  tags = merge(
    {
      "Name" = "${var.environment}-${var.project}-splunk-formatter-lambda-logs"
    },
    var.common_tags,
  )
}

resource "aws_iam_role" "cloudwatch_to_firehose_trust" {
  name        = "${var.environment}-${var.project}-cloudwatch-to-firehose-role"
  description = "Role for CloudWatch Log Group subscription"

  assume_role_policy = <<ROLE
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "logs.${var.aws_region}.amazonaws.com"
      }
    }
  ],
  "Version": "2012-10-17"
}
ROLE

}

data "aws_iam_policy_document" "cloudwatch_to_fh_access_policy" {
  statement {
    actions = [
      "firehose:*",
    ]

    effect = "Allow"

    resources = [
      aws_kinesis_firehose_delivery_stream.splunk_kinesis_firehose.arn
    ]
  }

  statement {
    actions = [
      "iam:PassRole",
    ]

    effect = "Allow"

    resources = [
      aws_iam_role.cloudwatch_to_firehose_trust.arn,
    ]
  }
}

resource "aws_iam_policy" "cloudwatch_to_firehose_access_policy" {
  name        = "${var.environment}-${var.project}-cloudwatch-to-firehose-policy"
  description = "Policy for Cloudwatch Subscription Filters to send logs to Firehose"
  policy      = data.aws_iam_policy_document.cloudwatch_to_fh_access_policy.json
}

resource "aws_iam_role_policy_attachment" "cloudwatch_to_firehose" {
  role       = aws_iam_role.cloudwatch_to_firehose_trust.name
  policy_arn = aws_iam_policy.cloudwatch_to_firehose_access_policy.arn
}