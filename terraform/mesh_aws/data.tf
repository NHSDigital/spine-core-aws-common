data "aws_caller_identity" "current" {}

resource "aws_vpc_endpoint" "private_s3" {
  vpc_id       = var.config.vpc_id
  service_name = "com.amazonaws.eu-west-2.s3"
}
