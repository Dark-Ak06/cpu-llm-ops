module "inference_vm" {
  source = "../../modules/inference_vm"

  environment   = var.environment
  instance_type = var.instance_type
  vpc_id        = var.vpc_id
  subnet_id     = var.subnet_id

  tags = {
    Project   = "cpu-llm-ops"
    ManagedBy = "Terraform"
  }
}
