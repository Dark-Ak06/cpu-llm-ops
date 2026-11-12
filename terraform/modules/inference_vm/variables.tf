variable "environment" {
  description = "Target environment name (e.g. staging, prod)"
  type        = string
  default     = "production"
}

variable "instance_type" {
  description = "AWS EC2 instance type optimized for CPU inference (e.g. c6i.xlarge or t3.xlarge)"
  type        = string
  default     = "c6i.xlarge"
}

variable "ami_id" {
  description = "Custom AMI ID. If null, latest Ubuntu 22.04 LTS is discovered dynamically."
  type        = string
  default     = null
}

variable "vpc_id" {
  description = "VPC ID where the instance and security group will be created"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID where the instance will be launched"
  type        = string
}

variable "allowed_ingress_cidrs" {
  description = "CIDR blocks permitted to access the inference endpoint (:8000)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "volume_size_gb" {
  description = "Size of root EBS volume in GiB to accommodate model cache and Docker storage"
  type        = number
  default     = 50
}

variable "tags" {
  description = "Additional tags to associate with provisioned resources"
  type        = map(string)
  default     = {}
}
