variable "name_prefix" {
  description = "Name to prefix on to the resources"
  type        = string
}

variable "cloudwatch_log_groups_to_forward" {
  description = "List of Cloudwatch Log Group Names to forward"
  type        = list(string)
  default     = []
}

variable "cloudwatch_retention_in_days" {
  description = "How many days to retain CloudWatch logs for"
  type        = number
  default     = 365
}

variable "s3logs_retention_in_days" {
  description = "How many days to retain S3 object logs for"
  type        = number
  default     = 7

  validation {
    condition     = var.s3logs_retention_in_days >= 1
    error_message = "The s3logs_retention_in_days value must be greater than or equal to 1."
  }
}

variable "splunk_source_type" {
  description = "TODO"
  type        = string
}

variable "splunk_hec_endpoint" {
  description = "TODO"
  type        = string
}

variable "splunk_hec_token" {
  description = "TODO"
  type        = string
  sensitive   = true
}

variable "splunk_index" {
  description = "TODO need to create a mapping of log levels to indexes"
  type        = string
}
