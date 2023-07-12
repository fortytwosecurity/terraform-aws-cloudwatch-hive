resource "random_string" "random" {
  length  = 4
  lower   = true
  special = false
  upper   = false
}

module "hive_alarm_cloudwatch_event" {
  source = "git::https://github.com/cloudposse/terraform-aws-cloudwatch-events.git?ref=0.6.1"
  name   = "hive_alarm_cloudwatch-${random_string.random.id}"

  cloudwatch_event_rule_description = var.cloudwatch_event_rule_description
  cloudwatch_event_rule_pattern     = var.cloudwatch_event_rule_pattern
  cloudwatch_event_target_arn       = module.alarm_to_hive_lambda.lambda_function_arn
}

module "hive_alarm_iam_assumable_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "4.10.1"

  trusted_role_services = [
    "lambda.amazonaws.com"
  ]

  create_role = true

  role_name         = "AlarmToHiveFindingsLambdaRole-${random_string.random.id}"
  role_requires_mfa = false

  custom_role_policy_arns = [
    module.hive_alarm_iam_policy.arn
  ]
}

data "aws_iam_policy_document" "hive_alarm_iam_policy" {
  statement {
    actions = [
      "cloudwatch:PutMetricData",
    ]

    resources = [
      "*"
    ]
  }

  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "*"
    ]
  }

  statement {
    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = [
      var.hive_api_secret_arn
    ]
  }

  statement {
    actions = [
      "kms:Decrypt",
    ]

    resources = [
      var.hive_api_secret_kms_key_arn
    ]
  }

}

module "hive_alarm_iam_policy" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-policy"
  version = "4.10.1"

  name        = "SechubToHiveFindingsLambda-Policy-${random_string.random.id}"
  path        = "/"
  description = "AlarmToHiveFindingsLambda-Policy"
  policy      = data.aws_iam_policy_document.hive_alarm_iam_policy.json
}

resource "aws_lambda_permission" "hive_alarm_allow_cloudwatch" {
  statement_id  = "PermissionForEventsToInvokeLambdachk-${random_string.random.id}"
  action        = "lambda:InvokeFunction"
  function_name = module.alarm_to_hive_lambda.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = module.hive_alarm_cloudwatch_event.aws_cloudwatch_event_rule_arn
}

data "archive_file" "alarm_to_hive_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/"
  output_path = "lambda_alarm_hive.zip"
}

module "thehive4py_layer" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "2.7.0"

  create_layer = true

  layer_name          = "thehive4py-layer-local"
  description         = "Lambda layer containing thehive4py"
  compatible_runtimes = ["python3.8"]

  create_package         = false
  local_existing_package = "${path.module}/layer.zip"
  tags                   = var.tags
}

module "alarm_to_hive_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "2.7.0"

  function_name  = "alarm-to-hive"
  description    = "function to send cloudwatch alarms to the hive"
  handler        = "lambda_alarm_hive.lambda_handler"
  runtime        = "python3.8"
  create_package = false

  local_existing_package = "lambda_alarm_hive.zip"

  environment_variables = {
    hiveSecretArn        = var.hive_api_secret_arn
    createHiveAlert      = var.create_hive_alert
    environment          = var.environment
    excludeAccountFilter = jsonencode(var.exclude_account_filter)
    excludeAlarmFilter   = jsonencode(var.exclude_alarm_filter)
    company              = var.company
    project              = var.project
    debug                = var.debug
  }

  layers = [
    module.thehive4py_layer.lambda_layer_arn,
  ]

  attach_policies    = true
  policies           = [module.hive_alarm_iam_policy.arn]
  number_of_policies = 1
  tags               = var.tags
}
