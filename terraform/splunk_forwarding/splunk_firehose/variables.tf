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
