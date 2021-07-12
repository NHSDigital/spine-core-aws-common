data "archive_file" "mesh_implementation_lambdas" {
  type        = "zip"
  source_dir  = "${path.module}/../../mesh_implementation_lambdas"
  output_path = "${path.module}/mesh_implementation_lambdas.zip"
}

resource "null_resource" "mesh_implementation_lambdas_dependencies" {
  triggers = {
    # hack so this always triggers
    mesh_implementation_lambdas_dependencies = timestamp()
  }
  provisioner "local-exec" {
    command = "/bin/bash ${path.module}/scripts/mesh_implementation_lambdas_dependencies.sh"
  }
}

data "archive_file" "mesh_implementation_lambdas_dependencies" {
  type        = "zip"
  source_dir  = "${path.module}/mesh_implementation_lambdas_dependencies"
  output_path = "${path.module}/mesh_implementation_lambdas_dependencies.zip"

  depends_on = [
    null_resource.mesh_implementation_lambdas_dependencies
  ]
}

resource "aws_lambda_layer_version" "mesh_implementation_lambdas_dependencies" {
  filename            = data.archive_file.mesh_implementation_lambdas_dependencies.output_path
  layer_name          = "mesh_implementation_lambdas_dependencies"
  source_code_hash    = data.archive_file.mesh_implementation_lambdas_dependencies.output_base64sha256
  compatible_runtimes = [local.python_runtime]

  depends_on = [
    null_resource.mesh_implementation_lambdas_dependencies
  ]
}
