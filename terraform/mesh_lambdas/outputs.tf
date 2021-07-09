output "output" {
  value = {
    config    = var.config
    mailboxes = module.mailboxes[*]
  }
}
