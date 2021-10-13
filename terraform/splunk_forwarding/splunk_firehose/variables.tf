variable "name_prefix" {
  description = "Name to prefix on to the resources"
  type        = string
}

variable "splunk_hec_endpoint" {
  type = string
}

variable "splunk_hec_token" {
  type      = string
  sensitive = true
}

variable "splunk_formatter" {
  description = "Splunk Formatter Lambda Output"
}
