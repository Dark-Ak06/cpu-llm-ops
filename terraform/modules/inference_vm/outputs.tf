output "instance_id" {
  description = "EC2 Instance ID of the provisioned inference host"
  value       = aws_instance.inference_vm.id
}

output "public_ip" {
  description = "Public IP address assigned to the inference host"
  value       = aws_instance.inference_vm.public_ip
}

output "private_ip" {
  description = "Private IP address of the inference host within the VPC"
  value       = aws_instance.inference_vm.private_ip
}

output "security_group_id" {
  description = "ID of the attached security group"
  value       = aws_security_group.inference.id
}
