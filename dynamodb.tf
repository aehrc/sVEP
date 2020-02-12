resource "aws_dynamodb_table" "datasets" {
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "APIid"
  name = "Datasets"

  attribute {
    name = "APIid"
    type = "S"
  }

}
