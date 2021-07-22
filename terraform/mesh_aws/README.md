# Mesh Lambdas

A terraform module to provide AWS infrastructure capable of sending and recieving Mesh messages

## Configuration

Example configuration required to use this module:

```
module "mesh" {
  source = "git::https://github.com/nhsdigital/spine-core-aws-common.git//terraform/mesh_aws?ref=mesh-v0.0.1"

  name_prefix = "example-project"

  config = {
    environment = "integration"
    verify_ssl  = true
  }

  mailboxes = [
      {
        id = "X26OT178"
        outbound_mappings = [
          {
            dest_mailbox = "X26OT179"
            workflow_id  = "TESTWORKFLOW"
          }
        ]
      },
      {
        id                = "X26OT179"
        outbound_mappings = []
      }
    ]
}
```

Release versions will be pushed to Github as git tags, with the format `mesh-v<major>.<minor>.<patch>` such as `mesh-v0.0.1`

## Tagging

We do not tag any resources created by this module, to configure tags across all supported resources, use the provider level default tags

Below is an example passing in Spines prefferred tags:

```
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
