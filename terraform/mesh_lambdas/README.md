# Mesh Lambdas

A terraform module to provide AWS infrastructure capable of sending and recieving Mesh messages

## Configuration

Example configuration required to use this module

```
module "mesh" {
  source = "git::https://github.com/nhsdigital/spine-core-aws-common.git//terraform/mesh_lambdas?ref=v0.0.4"

  name_prefix = "example-project-that-needs-mesh"

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
