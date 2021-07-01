variable "name_prefix" {
  description = "name to prefix on to the resources"
}

# TODO maybe break this into three configs?
variable "config" {
  description = "Shared Mesh configuration"

  type = object({
    ca_cert     = string # secret
    client_cert = string # secret
    client_key  = string # secret
    shared_key  = string # secret
    environment = string # integration|production
    verify_ssl  = bool
  })

  default = {
    ca_cert     = ""
    client_cert = ""
    client_key  = ""
    shared_key  = ""
    environment = ""
    verify_ssl  = true
  }

  validation {
    condition     = var.config.environment == "integration" || var.config.environment == "production"
    error_message = "The environment value must be either \"integration\" or \"production\"."
  }
}

variable "mailboxes" {
  description = "Configuration of Mesh mailboxes"

  type = list(object({
    id                   = string
    password             = string # secret
    allowed_senders      = string
    allowed_recipients   = string
    allowed_workflow_ids = string
    # inbound_bucket       = string # outputs not inputs
    # inbound_folder       = string # outputs not inputs
  }))

  default = []
}

variable "outbound_mappings" {
  description = "Configuration of Mesh outbound mappings"

  type = list(object({
    # bucket       = string # outputs not inputs
    # folder       = string # outputs not inputs
    src_mailbox  = string
    dest_mailbox = string
    workflow_id  = string
  }))

  default = []
}
