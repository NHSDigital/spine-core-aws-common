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