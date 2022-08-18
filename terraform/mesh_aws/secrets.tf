resource "aws_secretsmanager_secret" "client_key" {
  count = var.config.use_secrets_manager == "true" ? 1 : 0
  name      = "/${local.name}/mesh/MESH_CLIENT_KEY"
  description = "/${local.name}/mesh/MESH_CLIENT_KEY"
  kms_key_id  = aws_kms_key.mesh.key_id
}

resource "aws_secretsmanager_secret" "shared_key" {
  count = var.config.use_secrets_manager == "true" ? 1 : 0
  name      = "/${local.name}/mesh/MESH_SHARED_KEY"
  description = "/${local.name}/mesh/MESH_SHARED_KEY"
  kms_key_id  = aws_kms_key.mesh.key_id
}