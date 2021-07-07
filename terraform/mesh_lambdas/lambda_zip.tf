data "archive_file" "mesh_implementation_lambdas" {
  type        = "zip"
  source_dir  = "${path.module}/../../spine_aws_common/mesh/mesh_implementation_lambdas"
  output_path = "${path.module}/mesh_implementation_lambdas.zip"
}
