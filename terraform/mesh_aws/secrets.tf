resource "aws_secretsmanager_secret" "ca_cert" {
  name      = "/${local.name}/mesh/MESH_CA_CERT"
}
resource "aws_secretsmanager_secret" "client_cert" {
  name      = "/${local.name}/mesh/MESH_CLIENT_CERT"
}
resource "aws_secretsmanager_secret" "client_key" {
  name      = "/${local.name}/mesh/MESH_CLIENT_KEY"
}

resource "aws_secretsmanager_secret" "shared_key" {
  name      = "/${local.name}/mesh/MESH_SHARED_KEY"
}

resource "aws_secretsmanager_secret" "url" {
  name      = "/${local.name}/mesh/MESH_URL"
}

resource "aws_secretsmanager_secret" "verify_ssl" {
  name      = "/${local.name}/mesh/MESH_VERIFY_SSL"
}
