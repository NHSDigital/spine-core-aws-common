variable "environment" {
  type = string
  validation {
    condition     = var.environment == ""
    error_message = "Please provide a value for the Terraform workspace"
  }
}

variable "project" {
  type = string
  validation {
    condition     = var.project == ""
    error_message = "Please provide a value for the Project"
  }
}

variable "splunk_hec_endpoint" {
  default = ""
  type    = string
}

variable "splunk_hec_token" {
  default   = ""
  type      = string
  sensitive = true
}

variable "aws_region" {
  default = "eu-west-2"
  type    = string
}

variable "kms_key_arn" {
  default = ""
  type    = string
}

variable "lambda_source_dir" {
  type = string
  validation {
    condition     = var.lambda_source_dir == ""
    error_message = "Please provide a value for the Lambda Source Directory"
  }
}

variable "lambda_output_path" {
  type = string
  validation {
    condition     = var.lambda_output_path == ""
    error_message = "Please provide a value for the Lambda Output Path"
  }
}

variable "lambda_handler" {
  default = "cw_logs_to_splunk.handler"
  type    = string
}

variable "lambda_memory" {
  default = 128
  type    = number
}

variable "lambda_env_vars" {
  default = {}
  type    = map(string)
}

variable "common_tags" {
  default = {
    TagVersion         = "1"
    Programme          = "SpineCore"
    Project            = var.project
    DataClassification = var.environment == "prod" ? "5" : "1"
    Environment        = var.environment
    ServiceCategory    = var.environment == "prod" ? "Bronze" : "N/A"
    OnOffPattern       = "AlwaysOn"
    Tool               = "terraform"
  }
  type = map(string)
}