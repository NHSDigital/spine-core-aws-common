resource "null_resource" "splunk_formatter" {
  provisioner "local-exec" {
    command = "/bin/bash ${path.module}/scripts/build.sh"
  }

  triggers = {
    # hack so this always triggers
    splunk_formatter_dependencies = timestamp()
  }
}

data "archive_file" "splunk_formatter_archive" {
  type        = "zip"
  source_dir  = "${path.module}/build/splunk_formatter"
  output_path = "${path.module}/build/splunk_formatter.zip"

  depends_on = [
    null_resource.splunk_formatter
  ]
}

resource "null_resource" "splunk_formatter_dependencies" {
  provisioner "local-exec" {
    command = "/bin/bash ${path.module}/scripts/dependencies.sh"
  }

  triggers = {
    # hack so this always triggers
    splunk_formatter_dependencies = timestamp()
  }
}

data "archive_file" "splunk_formatter_dependencies" {
  type        = "zip"
  source_dir  = "${path.module}/build/splunk_formatter_dependencies"
  output_path = "${path.module}/build/splunk_formatter_dependencies.zip"

  depends_on = [
    null_resource.splunk_formatter_dependencies
  ]
}

resource "aws_lambda_layer_version" "splunk_formatter_dependencies" {
  filename            = data.archive_file.splunk_formatter_dependencies.output_path
  layer_name          = "splunk_formatter_dependencies"
  source_code_hash    = data.archive_file.splunk_formatter_dependencies.output_base64sha256
  compatible_runtimes = [local.runtime]
}
