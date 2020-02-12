locals {
  api_version = "v1.0.0"
}

#
# queryVCF Lambda Function
#
module "lambda-queryVCF" {
  source = "github.com/claranet/terraform-aws-lambda"

  function_name = "queryVCF"
  description = "Invokes infoSplitter for each dataset and returns result"
  handler = "lambda_function.lambda_handler"
  runtime = "python3.6"
  memory_size = 2048
  timeout = 28
  policy = {
    json = data.aws_iam_policy_document.lambda-queryVCF.json
  }
  source_path = "${path.module}/lambda/queryVCF"
  #tags = "${var.common-tags}"

  environment ={
    variables = {
      DATASETS_TABLE = "${aws_dynamodb_table.datasets.name}"
      QUERY_GTF_SNS_TOPIC_ARN = "${aws_sns_topic.queryGTF.arn}"
      QUERY_VCF_EXTENDED_SNS_TOPIC_ARN = "${aws_sns_topic.queryVCFExtended.arn}"
      CONCAT_SNS_TOPIC_ARN = "${aws_sns_topic.concat.arn}"
    }
  }
}

#
# queryVCFExtended Lambda Function
#
module "lambda-queryVCFExtended" {
  source = "github.com/claranet/terraform-aws-lambda"

  function_name = "queryVCFExtended"
  description = "Invokes infoSplitter for each dataset and returns result"
  handler = "lambda_function.lambda_handler"
  runtime = "python3.6"
  memory_size = 2048
  timeout = 28
  policy = {
    json = data.aws_iam_policy_document.lambda-queryVCFExtended.json
  }
  source_path = "${path.module}/lambda/queryVCFExtended"
  #tags = "${var.common-tags}"

  environment ={
    variables = {
      DATASETS_TABLE = "${aws_dynamodb_table.datasets.name}"
      QUERY_GTF_SNS_TOPIC_ARN = "${aws_sns_topic.queryGTF.arn}"
      QUERY_VCF_EXTENDED_SNS_TOPIC_ARN = "${aws_sns_topic.queryVCFExtended.arn}"
      CONCAT_SNS_TOPIC_ARN = "${aws_sns_topic.concat.arn}"
    }
  }
}

#
# queryGTF Lambda Function
#
module "lambda-queryGTF" {
  source = "github.com/claranet/terraform-aws-lambda"
  function_name = "queryGTF"
  description = "Queries GTF for a specified VCF regions."
  handler = "lambda_function.lambda_handler"
  runtime = "python3.6"
  memory_size = 2048
  timeout = 24
  policy = {
    json = data.aws_iam_policy_document.lambda-queryGTF.json
  }
  source_path = "${path.module}/lambda/queryGTF"
  #tags = "${var.common-tags}"
  environment ={
    variables = {
      DATASETS_TABLE = "${aws_dynamodb_table.datasets.name}"
      REFERENCE_GENOME = "s3://svep/sorted_filtered_Homo_sapiens.GRCh38.98.chr.gtf.gz"
      PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN = "${aws_sns_topic.pluginConsequence.arn}"
      PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN = "${aws_sns_topic.pluginUpdownstream.arn}"
    }
  }

}

#
# pluginConsequence Lambda Function
#
module "lambda-pluginConsequence" {
  source = "github.com/claranet/terraform-aws-lambda"
  function_name = "pluginConsequence"
  description = "Queries VCF for a specified variant."
  handler = "VEP.handle"
  runtime = "provided"
  memory_size = 2048
  timeout = 24
  policy = {
    json = data.aws_iam_policy_document.lambda-pluginConsequence.json
  }
  source_path = "${path.module}/lambda/pluginConsequence"
  #tags = "${var.common-tags}"
  layers =[
    "arn:aws:lambda:ap-southeast-2:445285296882:layer:perl-5-30-runtime:5",
    "arn:aws:lambda:ap-southeast-2:132838717167:layer:serverlessrepo-lambda-layer-awscli:1"
  ]
  environment ={
    variables = {
      SVEP_REGIONS = "${aws_s3_bucket.svep-regions.bucket}"
      REFERENCE_LOCATION = "s3://svep/"
    }
  }
}

#
# pluginUpdownstream Lambda Function
#
module "lambda-pluginUpdownstream" {
  source = "github.com/claranet/terraform-aws-lambda"
  function_name = "pluginUpdownstream"
  description = "Write upstream and downstream gene variant to temp bucket."
  handler = "lambda_function.lambda_handler"
  runtime = "python3.6"
  memory_size = 2048
  timeout = 24
  policy = {
    json = data.aws_iam_policy_document.lambda-pluginUpdownstream.json
  }
  source_path = "${path.module}/lambda/pluginUpdownstream"
  #tags = "${var.common-tags}"
  environment ={
    variables = {
      REFERENCE_GENOME = "s3://svep/transcripts_Homo_sapiens.GRCh38.98.chr.gtf.gz"
      SVEP_REGIONS = "${aws_s3_bucket.svep-regions.bucket}"
      CONCAT_SNS_TOPIC_ARN = "${aws_sns_topic.concat.arn}"
    }
  }
}

#
# concat Lambda Function
#
module "lambda-concat" {
  source = "github.com/claranet/terraform-aws-lambda"

  function_name = "concat"
  description = "concatenates all the temp files from SVEP_REGIONS bucket and push to SVEP_RESULTS"
  handler = "lambda_function.lambda_handler"
  runtime = "python3.6"
  memory_size = 2048
  timeout = 28
  policy = {
    json = data.aws_iam_policy_document.lambda-concat.json
  }
  source_path = "${path.module}/lambda/concat"
  #tags = "${var.common-tags}"

  environment ={
    variables = {
      DATASETS_TABLE = "${aws_dynamodb_table.datasets.name}"
      SVEP_REGIONS = "${aws_s3_bucket.svep-regions.bucket}"
      SVEP_RESULTS = "${aws_s3_bucket.svep-results.bucket}"
      CONCAT_SNS_TOPIC_ARN = "${aws_sns_topic.concat.arn}"
    }
  }
}
