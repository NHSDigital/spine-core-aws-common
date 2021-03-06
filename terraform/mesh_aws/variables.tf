variable "name_prefix" {
  description = "Name to prefix on to the resources"
}

variable "config" {
  description = "Shared Mesh configuration"

  type = object({
    environment = string
    verify_ssl  = bool
  })

  default = {
    environment = "integration"
    verify_ssl  = true
  }

  validation {
    condition     = var.config.environment == "integration" || var.config.environment == "production"
    error_message = "The environment value must be either \"integration\" or \"production\"."
  }
}

variable "mailboxes" {
  description = "Configuration of Mesh mailboxes"

  # TODO make outbound_mappings optional
  type = list(object({
    id                   = string
    allowed_recipients   = optional(string)
    allowed_senders      = optional(string)
    allowed_workflow_ids = optional(string)
    outbound_mappings = list(object({
      dest_mailbox = string
      workflow_id  = string
    }))
  }))

  default = []
}

variable "account_admin_role" {
  description = "Administrative Account Role used for policies that require owners, like KMS"
  type        = string
  default     = "NHSDAdminRole"
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
