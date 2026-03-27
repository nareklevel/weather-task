module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "vpc-weather-task"
  cidr = "10.77.0.0/16"

  azs = ["us-east-1a", "us-east-1b"]

  private_subnets = [
    "10.77.1.0/24",
    "10.77.2.0/24"
  ]

  public_subnets = [
    "10.77.3.0/24",
    "10.77.4.0/24"
  ]

  enable_nat_gateway = true
  single_nat_gateway = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = {
    Terraform   = "true"
    Environment = "dev"
  }
}