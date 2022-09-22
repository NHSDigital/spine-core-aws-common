data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_vpc_endpoint" "s3" {
  vpc_id       = var.config.vpc_id
  service_name = "com.amazonaws.eu-west-2.s3"
}
