terraform {
  backend "s3" {
    bucket = "terraform-states-svep"
    key = "terraform.tfstate"
    region = "ap-southeast-2"
    dynamodb_table = "terraform-state-locks"
  }
}
