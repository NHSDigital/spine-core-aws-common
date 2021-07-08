# Mesh Lambdas

A terraform module to provide AWS infrastructure capable of sending and recieving Mesh messages

## Configuration

_*TODO*_

```
variable "name_prefix" {
  description = "name to prefix on to the resources"
}

variable "config" {
  description = "Shared Mesh configuration"

  type = object({
    # ca_cert     = string # secret
    # client_cert = string # secret
    # client_key  = string # secret
    environment = string
    # shared_key  = string # secret
    verify_ssl = bool
  })

  default = {
    # ca_cert     = ""
    # client_cert = ""
    # client_key  = ""
    environment = "integration"
    # shared_key  = ""
    verify_ssl = true
  }

  validation {
    condition     = var.config.environment == "integration" || var.config.environment == "production"
    error_message = "The environment value must be either \"integration\" or \"production\"."
  }
}

variable "mailboxes" {
  description = "Configuration of Mesh mailboxes"

  type = list(object({
    allowed_recipients   = string
    allowed_senders      = string
    allowed_workflow_ids = string
    id                   = string
    # password             = string # secret
    # inbound_folder       = string # outputs not inputs
    outbound_mappings = list(object({
      dest_mailbox = string
      # src_mailbox  = string # is id
      workflow_id = string
      # folder       = string # outputs not inputs
    }))
  }))

  default = []
}
```
