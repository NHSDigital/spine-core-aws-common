locals {
  name        = "${var.name_prefix}-splunk-formatter"
  timeout     = 360
  memory_size = 128
  runtime     = "python3.9"
}
