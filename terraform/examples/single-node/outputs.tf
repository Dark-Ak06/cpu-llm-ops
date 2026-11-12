output "instance_id" {
  description = "Provisioned EC2 instance ID"
  value       = module.inference_vm.instance_id
}

output "public_ip" {
  description = "Public IP address of inference host"
  value       = module.inference_vm.public_ip
}

output "api_endpoint" {
  description = "HTTP inference API endpoint"
  value       = "http://${module.inference_vm.public_ip}:8000"
}

output "grafana_endpoint" {
  description = "Grafana dashboard endpoint"
  value       = "http://${module.inference_vm.public_ip}:3000"
}
