variable "name_prefix" {
  description = "Name to prefix on to the resources"
  type        = string
}

variable "splunk_hec_endpoint" {
  description = "The Splunk HTTPS endpoint URL to send logs to"
  type        = string
}

variable "splunk_hec_token" {
  description = "The Splunk Endpoint token to authenticate with"
  type        = string
  sensitive   = true
}

variable "splunk_formatter" {
  description = "Splunk Formatter Lambda Output"
}

variable "kms_s3_key_arn" {
  description = "KMS Key for S3 encryption"
  type        = string
}

variable "kms_cloudwatch_key_arn" {
  description = "KMS Key for Cloudwatch log encryption"
  type        = string
}
