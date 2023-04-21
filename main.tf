locals {
  api_version = "v1.0.0"
  slice_size_mbp = 5
}

#
# initQuery Lambda Function
#
module "lambda-initQuery" {
  source = "github.com/bhosking/terraform-aws-lambda"

  function_name = "initQuery"
  description = "Invokes queryVCF with the calculated regions"
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  memory_size = 1792
  timeout = 28
  policy = {
    json = data.aws_iam_policy_document.lambda-initQuery.json
  }
  source_path = "${path.module}/lambda/initQuery"
  #tags = var.common-tags

  environment ={
    variables = {
      QUERY_VCF_SNS_TOPIC_ARN = aws_sns_topic.queryVCF.arn
      SLICE_SIZE_MBP = local.slice_size_mbp
    }
  }
}

#
# queryVCF Lambda Function
#
module "lambda-queryVCF" {
  source = "github.com/bhosking/terraform-aws-lambda"

  function_name = "queryVCF"
  description = "Invokes queryGTF for each region."
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  memory_size = 2048
  timeout = 28
  policy = {
    json = data.aws_iam_policy_document.lambda-queryVCF.json
  }
  source_path = "${path.module}/lambda/queryVCF"
  #tags = var.common-tags

  environment ={
    variables = {
      SVEP_TEMP = aws_s3_bucket.svep-temp.bucket
      QUERY_GTF_SNS_TOPIC_ARN = aws_sns_topic.queryGTF.arn
      QUERY_VCF_SNS_TOPIC_ARN = aws_sns_topic.queryVCF.arn
      QUERY_VCF_SUBMIT_SNS_TOPIC_ARN = aws_sns_topic.queryVCFsubmit.arn
      SLICE_SIZE_MBP = local.slice_size_mbp
    }
  }
}

#
# queryVCFsubmit Lambda Function
#
module "lambda-queryVCFsubmit" {
  source = "github.com/bhosking/terraform-aws-lambda"

  function_name = "queryVCFsubmit"
  description = "This lambda will be called if there are too many batchids to be processed within"
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  memory_size = 2048
  timeout = 28
  policy = {
    json = data.aws_iam_policy_document.lambda-queryVCFsubmit.json
  }
  source_path = "${path.module}/lambda/queryVCFsubmit"
  #tags = var.common-tags

  environment ={
    variables = {
      SVEP_TEMP = aws_s3_bucket.svep-temp.bucket
      QUERY_GTF_SNS_TOPIC_ARN = aws_sns_topic.queryGTF.arn
      QUERY_VCF_SUBMIT_SNS_TOPIC_ARN = aws_sns_topic.queryVCFsubmit.arn
    }
  }
}

#
# queryGTF Lambda Function
#
module "lambda-queryGTF" {
  source = "github.com/bhosking/terraform-aws-lambda"
  function_name = "queryGTF"
  description = "Queries GTF for a specified VCF regions."
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  memory_size = 2048
  timeout = 24
  policy = {
    json = data.aws_iam_policy_document.lambda-queryGTF.json
  }
  source_path = "${path.module}/lambda/queryGTF"
  #tags = var.common-tags
  environment ={
    variables = {
      SVEP_TEMP = aws_s3_bucket.svep-temp.bucket
      REFERENCE_GENOME = "sorted_filtered_Homo_sapiens.GRCh38.109.chr.gtf.gz"
      PLUGIN_CONSEQUENCE_SNS_TOPIC_ARN = aws_sns_topic.pluginConsequence.arn
      PLUGIN_UPDOWNSTREAM_SNS_TOPIC_ARN = aws_sns_topic.pluginUpdownstream.arn
      QUERY_GTF_SNS_TOPIC_ARN = aws_sns_topic.queryGTF.arn
    }
  }
}


#
# pluginConsequence Lambda Function
#
module "lambda-pluginConsequence" {
  source = "github.com/bhosking/terraform-aws-lambda"
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
  #tags = var.common-tags
  layers =[
    "arn:aws:lambda:ap-southeast-2:445285296882:layer:perl-5-30-runtime:5",
    "arn:aws:lambda:ap-southeast-2:132838717167:layer:serverlessrepo-lambda-layer-awscli:1"
  ]
  environment ={
    variables = {
      SVEP_TEMP = aws_s3_bucket.svep-temp.bucket
      SVEP_REGIONS = aws_s3_bucket.svep-regions.bucket
      REFERENCE_LOCATION = "s3://svep/"
      SPLICE_REFERENCE = "sorted_splice_GRCh38.109.gtf.gz"
      MIRNA_REFERENCE = "sorted_filtered_mirna.gff3.gz" 
    }
  }
}

#
# pluginUpdownstream Lambda Function
#
module "lambda-pluginUpdownstream" {
  source = "github.com/bhosking/terraform-aws-lambda"
  function_name = "pluginUpdownstream"
  description = "Write upstream and downstream gene variant to temp bucket."
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  memory_size = 2048
  timeout = 24
  policy = {
    json = data.aws_iam_policy_document.lambda-pluginUpdownstream.json
  }
  source_path = "${path.module}/lambda/pluginUpdownstream"
  #tags = var.common-tags
  environment ={
    variables = {
      SVEP_TEMP = aws_s3_bucket.svep-temp.bucket
      REFERENCE_GENOME = "transcripts_Homo_sapiens.GRCh38.109.chr.gtf.gz"
      SVEP_REGIONS = aws_s3_bucket.svep-regions.bucket
      CONCAT_STARTER_SNS_TOPIC_ARN = aws_sns_topic.concatStarter.arn
    }
  }
}

#
# concat Lambda Function
#
module "lambda-concat" {
  source = "github.com/bhosking/terraform-aws-lambda"

  function_name = "concat"
  description = "Triggers createPages."
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  memory_size = 2048
  timeout = 28
  policy = {
    json = data.aws_iam_policy_document.lambda-concat.json
  }
  source_path = "${path.module}/lambda/concat"
  #tags = var.common-tags

  environment ={
    variables = {
      SVEP_REGIONS = aws_s3_bucket.svep-regions.bucket
      CREATEPAGES_SNS_TOPIC_ARN = aws_sns_topic.createPages.arn
    }
  }
}

#
# concatStarter Lambda Function
#
module "lambda-concatStarter" {
  source = "github.com/bhosking/terraform-aws-lambda"

  function_name = "concatStarter"
  description = "Validates all processing is done and triggers concat"
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  memory_size = 128
  timeout = 28
  policy = {
    json = data.aws_iam_policy_document.lambda-concatStarter.json
  }
  source_path = "${path.module}/lambda/concatStarter"
  #tags = var.common-tags

  environment ={
    variables = {
      SVEP_TEMP = aws_s3_bucket.svep-temp.bucket
      SVEP_REGIONS = aws_s3_bucket.svep-regions.bucket
      CONCAT_SNS_TOPIC_ARN = aws_sns_topic.concat.arn
      CONCAT_STARTER_SNS_TOPIC_ARN = aws_sns_topic.concatStarter.arn
    }
  }
}

#
# createPages Lambda Function
#
module "lambda-createPages" {
  source = "github.com/bhosking/terraform-aws-lambda"

  function_name = "createPages"
  description = "concatenates individual page with 700 entries, received from concat lambda"
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  memory_size = 2048
  timeout = 28
  policy = {
    json = data.aws_iam_policy_document.lambda-createPages.json
  }
  source_path = "${path.module}/lambda/createPages"
  #tags = var.common-tags

  environment ={
    variables = {
      SVEP_REGIONS = aws_s3_bucket.svep-regions.bucket
      SVEP_RESULTS = aws_s3_bucket.svep-results.bucket
      CONCATPAGES_SNS_TOPIC_ARN = aws_sns_topic.concatPages.arn
      CREATEPAGES_SNS_TOPIC_ARN = aws_sns_topic.createPages.arn
    }
  }
}

#
# concatPages Lambda Function
#
module "lambda-concatPages" {
  source = "github.com/bhosking/terraform-aws-lambda"

  function_name = "concatPages"
  description = "concatenates all the page files created by createPages lambda."
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  memory_size = 2048
  timeout = 28
  policy = {
    json = data.aws_iam_policy_document.lambda-concatPages.json
  }
  source_path = "${path.module}/lambda/concatPages"
  #tags = var.common-tags

  environment ={
    variables = {
      SVEP_REGIONS = aws_s3_bucket.svep-regions.bucket
      SVEP_RESULTS = aws_s3_bucket.svep-results.bucket
      CONCATPAGES_SNS_TOPIC_ARN = aws_sns_topic.concatPages.arn
    }
  }
}
