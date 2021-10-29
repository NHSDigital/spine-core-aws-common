module "splunk_firehose" {
  source = "./splunk_firehose"

  name_prefix            = var.name_prefix
  kms_cloudwatch_key_arn = module.kms.key.arn
  kms_s3_key_arn         = module.kms.key.arn
  splunk_formatter       = module.splunk_formatter.lambda
  splunk_hec_endpoint    = var.splunk_hec_endpoint
  splunk_hec_token       = var.splunk_hec_token
}

module "splunk_formatter" {
  source = "./splunk_formatter"

  name_prefix                      = var.name_prefix
  cloudwatch_log_groups_to_forward = var.cloudwatch_log_groups_to_forward
  kms_cloudwatch_key_arn           = module.kms.key.arn
  splunk_firehose                  = module.splunk_firehose.firehose
  splunk_indexes_to_logs_levels    = var.splunk_indexes_to_logs_levels
  splunk_sourcetype                = var.splunk_sourcetype
}

module "cloudwatch_subscriptions" {
  source = "./cloudwatch_subscriptions"

  name_prefix                      = var.name_prefix
  cloudwatch_log_groups_to_forward = var.cloudwatch_log_groups_to_forward
  splunk_firehose                  = module.splunk_firehose.firehose
}

module "kms" {
  source = "./kms_key"

  name        = "splunk_forwarding"
  environment = var.name_prefix
}
