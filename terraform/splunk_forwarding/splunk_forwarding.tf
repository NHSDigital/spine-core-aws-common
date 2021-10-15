module "splunk_firehose" {
  source              = "./splunk_firehose"
  name_prefix         = var.name_prefix
  splunk_formatter    = module.splunk_formatter.lambda
  splunk_hec_endpoint = var.splunk_hec_endpoint
  splunk_hec_token    = var.splunk_hec_token
}

module "splunk_formatter" {
  source                        = "./splunk_formatter"
  name_prefix                   = var.name_prefix
  splunk_firehose               = module.splunk_firehose.firehose
  splunk_indexes_to_logs_levels = var.splunk_indexes_to_logs_levels
  splunk_source_type_prefix     = var.splunk_source_type_prefix
}

module "cloudwatch_subscriptions" {
  source                           = "./cloudwatch_subscriptions"
  name_prefix                      = var.name_prefix
  cloudwatch_log_groups_to_forward = var.cloudwatch_log_groups_to_forward
  splunk_firehose                  = module.splunk_firehose.firehose
}
