variable "name_prefix" {
  description = "Name to prefix on to the resources"
  type        = string
}

variable "splunk_source_type_prefix" {
  description = "A prefix to apply to all Splunk source types"
  type        = string
}

variable "splunk_indexes_to_logs_levels" {
  description = "A mapping of log levels to Splunk Indexes"
  type        = object({})
}

variable "splunk_firehose" {
  description = "Splunk Firehose Output"
}
