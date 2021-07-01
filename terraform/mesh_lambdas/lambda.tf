locals {
  lambdas = [
    "check-send-parameters",
    "send-message-chunk",
    "get-store-message-chunk",
    "poll-for-messages",
  ]
}

module "lambda" {
  for_each = toset(local.lambdas)

  source = "./../modules/lambda"

  function_name = "${local.name}-${each.key}"
  code_name     = each.key
}
