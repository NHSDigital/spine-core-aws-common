locals {
  name = "${var.name_prefix}-mesh"

  mesh_url = {
    integration = "https://msg.intspineservices.nhs.uk"
    production  = "https://mesh-sync.spineservices.nhs.uk"
  }

  python_runtime = "python3.8"
  lambda_timeout = 300
}
