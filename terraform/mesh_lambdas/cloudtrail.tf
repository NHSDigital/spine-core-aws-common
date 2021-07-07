resource "aws_cloudtrail" "foobar" {
  name                          = "${local.name}-s3logs"
  s3_bucket_name                = aws_s3_bucket.s3logs.id
  s3_key_prefix                 = "AWSLogs/"
  include_global_service_events = false
  is_multi_region_trail         = true
  enable_log_file_validation    = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true

    data_resource {
      type = "AWS::S3::Object"
      values = [
        "${aws_s3_bucket.mesh.arn}/"
      ]
    }
  }
}
