variable "name_prefix" {
  description = "Name to prefix on to the resources"
  type        = string
}

variable "cloudwatch_log_groups_to_forward" {
  description = "List of Cloudwatch Log Group Names to forward"
  type        = list(string)
  default     = []
}

variable "splunk_firehose" {
  description = "Splunk Firehose Output"
}
