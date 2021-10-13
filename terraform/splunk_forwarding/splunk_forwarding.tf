module "splunk_firehose" {
  source              = "./splunk_firehose"
  name_prefix         = var.name_prefix
  splunk_formatter    = module.splunk_formatter.lambda
  splunk_hec_endpoint = var.splunk_hec_endpoint
  splunk_hec_token    = var.splunk_hec_token
}

module "splunk_formatter" {
  source             = "./splunk_formatter"
  name_prefix        = var.name_prefix
  splunk_source_type = var.splunk_source_type
  splunk_firehose    = module.splunk_firehose.firehose
  splunk_index       = var.splunk_index
}

module "cloudwatch_subscriptions" {
  source                           = "./cloudwatch_subscriptions"
  name_prefix                      = var.name_prefix
  splunk_firehose                  = module.splunk_firehose.firehose
  cloudwatch_log_groups_to_forward = var.cloudwatch_log_groups_to_forward
}
