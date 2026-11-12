variable "aws_region" {
  description = "Target AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "staging"
}

variable "instance_type" {
  description = "Compute instance type for CPU inference"
  type        = string
  default     = "c6i.xlarge"
}

variable "vpc_id" {
  description = "Target VPC ID"
  type        = string
  default     = "vpc-0123456789abcdef0"
}

variable "subnet_id" {
  description = "Target public subnet ID"
  type        = string
  default     = "subnet-0123456789abcdef0"
}
