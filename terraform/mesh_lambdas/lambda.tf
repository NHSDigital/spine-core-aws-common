locals {
  lambdas = [
    "fetch-message-chunk",
    "check-send-parameters",
    "poll-mailbox",
    "send-message-chunk",
  ]
}

module "lambda" {
  for_each = toset(local.lambdas)

  source = "./../modules/lambda"

  function_name = "${local.name}-${each.key}"
  code_name     = each.key
}
