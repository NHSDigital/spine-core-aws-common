locals {
  function_name = var.function_name
  code_name     = var.code_name

  python_runtime = "python3.8"
  lambda_timeout = 300
}
