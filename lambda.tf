#
# initQuery Lambda Function
#
resource "aws_lambda_permission" "APIinitQuery" {
  statement_id = "AllowinitQueryInvoke"
  action = "lambda:InvokeFunction"
  function_name = module.lambda-initQuery.function_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_api_gateway_rest_api.VPApi.execution_arn}/*/*/${aws_api_gateway_resource.submit.path_part}"
}
resource "aws_lambda_function_recursion_config" "APIinitQuery" {
  function_name = module.lambda-initQuery.function_name
  recursive_loop = "Allow"
}

#
# getResultsURL Lambda Function
#
resource "aws_lambda_permission" "APIgetResultsURL" {
  statement_id = "AllowgetResultsURLInvoke"
  action = "lambda:InvokeFunction"
  function_name = module.lambda-getResultsURL.function_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_api_gateway_rest_api.VPApi.execution_arn}/*/*/${aws_api_gateway_resource.results-url.path_part}"
}

#
# queryVCF Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaqueryVCF" {
  statement_id = "SNSLambdaqueryVCF"
  action = "lambda:InvokeFunction"
  function_name = module.lambda-queryVCF.function_name
  principal = "sns.amazonaws.com"
  source_arn = aws_sns_topic.queryVCF.arn
}
resource "aws_lambda_function_recursion_config" "SNSLambdaqueryVCF" {
  function_name = module.lambda-queryVCF.function_name
  recursive_loop = "Allow"
}

#
# queryVCFsubmit Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaqueryVCFsubmit" {
  statement_id = "SNSLambdaqueryVCFsubmit"
  action = "lambda:InvokeFunction"
  function_name = module.lambda-queryVCFsubmit.function_name
  principal = "sns.amazonaws.com"
  source_arn = aws_sns_topic.queryVCFsubmit.arn
}

#
# queryGTF Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaqueryGTF" {
  statement_id = "SNSLambdaqueryGTF"
  action = "lambda:InvokeFunction"
  function_name = module.lambda-queryGTF.function_name
  principal = "sns.amazonaws.com"
  source_arn = aws_sns_topic.queryGTF.arn
}
resource "aws_lambda_function_recursion_config" "SNSLambdaqueryGTF" {
  function_name = module.lambda-queryGTF.function_name
  recursive_loop = "Allow"
}


#
# pluginConsequence Lambda Function
#
resource "aws_lambda_permission" "SNSLambdapluginConsequence" {
  statement_id = "SNSLambdapluginConsequence"
  action = "lambda:InvokeFunction"
  # TODO: Update to reference function_name once terraform-aws-lambda is updated
  function_name = module.lambda-pluginConsequence.lambda_function_name
  principal = "sns.amazonaws.com"
  source_arn = aws_sns_topic.pluginConsequence.arn
}
resource "aws_lambda_function_recursion_config" "SNSLambdapluginConsequence" {
  # TODO: Update to reference function_name once terraform-aws-lambda is updated
  function_name = module.lambda-pluginConsequence.lambda_function_name
  recursive_loop = "Allow"
}


#
# pluginUpdownstream Lambda Function
#
resource "aws_lambda_permission" "SNSLambdapluginUpdownstream" {
  statement_id = "SNSLambdapluginUpdownstream"
  action = "lambda:InvokeFunction"
  function_name = module.lambda-pluginUpdownstream.function_name
  principal = "sns.amazonaws.com"
  source_arn = aws_sns_topic.pluginUpdownstream.arn
}

#
# concat Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaconcat" {
  statement_id = "SNSLambdaconcat"
  action = "lambda:InvokeFunction"
  function_name = module.lambda-concat.function_name
  principal = "sns.amazonaws.com"
  source_arn = aws_sns_topic.concat.arn
}

#
# concatStarter Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaconcatStarter" {
  statement_id = "SNSLambdaconcatStarter"
  action = "lambda:InvokeFunction"
  function_name = module.lambda-concatStarter.function_name
  principal = "sns.amazonaws.com"
  source_arn = aws_sns_topic.concatStarter.arn
}
resource "aws_lambda_function_recursion_config" "SNSLambdaconcatStarter" {
  function_name = module.lambda-concatStarter.function_name
  recursive_loop = "Allow"
}

#
# createPages Lambda Function
#
resource "aws_lambda_permission" "SNSLambdacreatePages" {
  statement_id = "SNSLambdacreatePages"
  action = "lambda:InvokeFunction"
  function_name = module.lambda-createPages.function_name
  principal = "sns.amazonaws.com"
  source_arn = aws_sns_topic.createPages.arn
}
resource "aws_lambda_function_recursion_config" "SNSLambdacreatePages" {
  function_name = module.lambda-createPages.function_name
  recursive_loop = "Allow"
}

#
# concatPages Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaconcatPages" {
  statement_id = "SNSLambdaconcatPages"
  action = "lambda:InvokeFunction"
  function_name = module.lambda-concatPages.function_name
  principal = "sns.amazonaws.com"
  source_arn = aws_sns_topic.concatPages.arn
}
