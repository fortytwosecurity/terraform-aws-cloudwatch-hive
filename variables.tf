variable "cloudwatch_event_rule_description" {
  type        = string
  description = "The description of the rule."
  default     = ""
}

variable "cloudwatch_event_rule_pattern" {
  description = "Event pattern described a HCL map which will be encoded as JSON with jsonencode function. See full documentation of CloudWatch Events and Event Patterns for details. http://docs.aws.amazon.com/AmazonCloudWatch/latest/DeveloperGuide/CloudWatchEventsandEventPatterns.html"
}

variable "company" {
  type        = string
  description = "company name"
  default     = ""
}

variable "create_hive_alert" {
  type        = bool
  description = "Boolean to configure lambda to create an issue. This requires a secret with url and apikey"
  default     = true
}

variable "debug" {
  type        = bool
  description = "Boolean to enable debugging logs"
  default     = true
}

variable "hive_api_secret_arn" {
  type        = string
  description = "ARN of secret that holds the hive url and api key"
}

variable "hive_api_secret_kms_key_arn" {
  type        = string
  description = "ARN of the KMS key protecting the hive api secret"
}

variable "project" {
  type        = string
  description = "Project name"
  default     = ""
}

variable "environment" {
  type        = string
  description = "Environment name"
  default     = ""
}

variable "exclude_account_filter" {
  type        = list(string)
  description = "A list of account IDs for which no alerts will be created"
  default     = []
}

variable "exclude_alarm_filter" {
  type        = list(string)
  description = "A list of alarm names for which no alerts will be created"
  default     = []
}

variable "tags" {
  type        = map(string)
  description = "Map of tags"
}
