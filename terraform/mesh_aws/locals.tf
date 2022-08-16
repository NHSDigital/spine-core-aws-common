locals {
  name = "${var.name_prefix}-mesh"

  mesh_url = {
    integration = "https://msg.intspineservices.nhs.uk"
    production  = "https://mesh-sync.spineservices.nhs.uk"
  }

  mesh_ips = {
    integration = [
      "3.11.177.31/32", "35.177.15.89/32", "3.11.199.83/32",       # Blue
      "35.178.64.126/32", "18.132.113.121/32", "18.132.31.159/32", # Green

    ]
    production = [
      "18.132.56.40/32", "3.11.193.200/32", "35.176.248.137/32", # Blue
      "3.10.194.216/32", "35.176.231.190/32", "35.179.50.16/32"  # Green
    ]
  }

  python_runtime = "python3.8"
  lambda_timeout = 300
}
