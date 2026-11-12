# Root terraform variables
variable "environment" {
  description = "Target deployment environment"
  type        = string
  default     = "production"
}
