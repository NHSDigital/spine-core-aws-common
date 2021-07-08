terraform {
  required_version = ">= 0.15.0"

  experiments = [
    module_variable_optional_attrs
  ]

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"
    }
  }
}
