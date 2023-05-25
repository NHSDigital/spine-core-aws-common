resource "aws_ssm_parameter" "ca_cert" {
  name      = "/${local.name}/mesh/cm-sending-group-id"
  type      = "SecureString"
  value     = "To Replace"
  overwrite = false

  lifecycle {
    ignore_changes = [
      value
    ]
  }
}