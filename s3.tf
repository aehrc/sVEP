resource "aws_s3_bucket" "svep-regions" {
  bucket_prefix = "svep-regions"
  force_destroy = true
}
resource "aws_s3_bucket" "svep-temp" {
  bucket_prefix = "svep-temp"
  force_destroy = true
}

resource "aws_s3_bucket" "svep-results" {
  bucket_prefix = "svep-results"
  force_destroy = true
}
