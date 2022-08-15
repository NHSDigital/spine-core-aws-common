resource "aws_secretsmanager_secret" "ca_cert" {
  name      = "/${local.name}/mesh/MESH_CA_CERT"
  overwrite = true
  type      = "SecureString"
  value     = "To Replace"

  lifecycle {
    ignore_changes = [
      value
    ]
  }
}
resource "aws_secretsmanager_secret" "client_cert" {
  name      = "/${local.name}/mesh/MESH_CLIENT_CERT"
  overwrite = true
  type      = "SecureString"
  value     = "To Replace"

  lifecycle {
    ignore_changes = [
      value
    ]
  }
}
resource "aws_secretsmanager_secret" "client_key" {
  name      = "/${local.name}/mesh/MESH_CLIENT_KEY"
  overwrite = true
  type      = "SecureString"
  value     = "To Replace"

  lifecycle {
    ignore_changes = [
      value
    ]
  }
}

resource "aws_secretsmanager_secret" "shared_key" {
  name      = "/${local.name}/mesh/MESH_SHARED_KEY"
  overwrite = true
  type      = "SecureString"
  value     = "To Replace"

  lifecycle {
    ignore_changes = [
      value
    ]
  }
}

resource "aws_secretsmanager_secret" "url" {
  name      = "/${local.name}/mesh/MESH_URL"
  overwrite = true
  type      = "String"
  value     = local.mesh_url[var.config.environment]
}

resource "aws_secretsmanager_secret" "verify_ssl" {
  name      = "/${local.name}/mesh/MESH_VERIFY_SSL"
  overwrite = true
  type      = "String"
  # This is effectively converting the bool type from Terraform to Python
  value = var.config.verify_ssl ? "True" : "False"
}
