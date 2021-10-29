variable "name_prefix" {
  description = "Name to prefix on to the resources"
  type        = string
}

variable "splunk_sourcetype" {
  description = "A Splunk `sourcetype` to apply to all logs"
  type        = string
}

variable "splunk_indexes_to_logs_levels" {
  description = "A mapping of log levels to Splunk Indexes"
}

variable "cloudwatch_log_groups_to_forward" {
  description = "List of Cloudwatch Log Group Names to forward"
  type        = list(string)
  default     = []
}

variable "splunk_firehose" {
  description = "Splunk Firehose Output"
}

variable "kms_cloudwatch_key_arn" {
  description = "KMS Key for Cloudwatch log encryption"
  type        = string
}
