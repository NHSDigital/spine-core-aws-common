data "archive_file" "mesh_implementation_lambdas" {
  type        = "zip"
  source_dir  = "${path.module}/../../mesh_implementation_lambdas"
  output_path = "${path.module}/mesh_implementation_lambdas.zip"
}

# TODO package in module?
# data "archive_file" "mesh_implementation_lambdas_dependencies" {
#   # TODO deps to package
#   # aws_lambda_powertools
#   # spine_aws_common
#   # requests
#   # urllib3
#   type        = "zip"
#   source_dir  = "${path.module}/../../spine_aws_common/mesh/mesh_implementation_lambdas_dependencies"
#   output_path = "${path.module}/mesh_implementation_lambdas_dependencies.zip"
# }

resource "aws_lambda_layer_version" "mesh_implementation_lambdas_dependencies" {
  # TODO package in module?
  # filename   = archive_file.mesh_implementation_lambdas_dependencies.output_path
  filename   = "${path.module}/../../spine_aws_common/mesh/mesh_implementation_lambdas_dependencies.zip"
  layer_name = "mesh_implementation_lambdas_dependencies"

  compatible_runtimes = [local.python_runtime]
}
