# Splunk Forwarding Terraform Module

A terraform module to provide the ability to forward a Cloudwatch Log group to Splunk

Using the main resources:

- Kinesis Firehose Stream, to take Cloudwatch logs, transform them and deliver them to Splunk
- Lambda Function, that transforms the Cloudwatch Logs to a Splunk ingestible format
- S3 Bucket, stores any logs that failed to be delivered to Splunk

## Configuration

Example configuration required to use this module:

- `name_prefix`: Name to prefix created resources
- `splunk_hec_endpoint`: Endpoint URL for the logs to be forwarded to
- `splunk_hec_token`: Authentication token for the Endpoint
- `splunk_source_type_prefix`: a prefix to apply to the standard source types
- `splunk_indexes_to_logs_levels`: mapping of Splunk Index to log levels for specific logs to be stored into
- `cloudwatch_log_groups_to_forward`: a list of log group names that will be forwarded

```hcl
module "splunk_forwarding" {
  source = "git::https://github.com/nhsdigital/spine-core-aws-common.git//terraform/splunk_forwarding?ref=v0.0.1"

  name_prefix = "example-project"

  splunk_hec_endpoint       = "https://example.endpoint.splunk.com/services/collector"
  splunk_hec_token          = "00000000-0000-0000-0000-000000000000"
  splunk_source_type_prefix = "example"
  splunk_indexes_to_logs_levels = {
    "aws"     = "aws_example"
    "audit"   = "audit_example"
    "default" = "app_example"
  }

  cloudwatch_log_groups_to_forward = [
    "/aws/lambda/first_example",
    "/aws/lambda/second_example",
    "/aws/lambda/third_example",
  ]
}
```

Release versions will be pushed to Github as git tags, with the format `v<major>.<minor>.<patch>` such as `v0.0.1`

## Tagging

We do not tag any resources created by this module, to configure tags across all supported resources, use the provider level default tags

Below is an example passing in Spine's preferred tags:

```hcl
provider "aws" {
  region  = "eu-west-2"
  profile = "default"

  default_tags {
    tags = {
      TagVersion         = "1"
      Programme          = "example-programme"
      Project            = "example-project"
      DataClassification = "5"
      Environment        = "preprod"
      ServiceCategory    = "Silver"
      Tool               = "terraform"
    }
  }
}
```
