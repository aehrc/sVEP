terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "5.69.0"
    }
    
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 3.0.2"
    }
  }
  required_version = ">= 0.13"
}
