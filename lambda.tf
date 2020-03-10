#
# queryVCF Lambda Function
#
resource "aws_lambda_permission" "APIqueryVCF" {
  statement_id = "AllowqueryVCFInvoke"
  action = "lambda:InvokeFunction"
  function_name = "${module.lambda-queryVCF.function_name}"
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_api_gateway_rest_api.VPApi.execution_arn}/*/*/${aws_api_gateway_resource.submit.path_part}"
}

#
# queryVCFsubmit Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaqueryVCFsubmit" {
  statement_id = "SNSLambdaqueryVCFsubmit"
  action = "lambda:InvokeFunction"
  function_name = "${module.lambda-queryVCFsubmit.function_name}"
  principal = "sns.amazonaws.com"
  source_arn = "${aws_sns_topic.queryVCFsubmit.arn}"
}

#
# queryVCFExtended Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaqueryVCFExtended" {
  statement_id = "SNSLambdaqueryVCFExtended"
  action = "lambda:InvokeFunction"
  function_name = "${module.lambda-queryVCFExtended.function_name}"
  principal = "sns.amazonaws.com"
  source_arn = "${aws_sns_topic.queryVCFExtended.arn}"
}

#
# queryGTF Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaqueryGTF" {
  statement_id = "SNSLambdaqueryGTF"
  action = "lambda:InvokeFunction"
  function_name = "${module.lambda-queryGTF.function_name}"
  principal = "sns.amazonaws.com"
  source_arn = "${aws_sns_topic.queryGTF.arn}"
}


#
# pluginConsequence Lambda Function
#
resource "aws_lambda_permission" "SNSLambdapluginConsequence" {
  statement_id = "SNSLambdapluginConsequence"
  action = "lambda:InvokeFunction"
  function_name = "${module.lambda-pluginConsequence.function_name}"
  principal = "sns.amazonaws.com"
  source_arn = "${aws_sns_topic.pluginConsequence.arn}"
}

#
# pluginUpdownstream Lambda Function
#
resource "aws_lambda_permission" "SNSLambdapluginUpdownstream" {
  statement_id = "SNSLambdapluginUpdownstream"
  action = "lambda:InvokeFunction"
  function_name = "${module.lambda-pluginUpdownstream.function_name}"
  principal = "sns.amazonaws.com"
  source_arn = "${aws_sns_topic.pluginUpdownstream.arn}"
}

#
# concat Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaconcat" {
  statement_id = "SNSLambdaconcat"
  action = "lambda:InvokeFunction"
  function_name = "${module.lambda-concat.function_name}"
  principal = "sns.amazonaws.com"
  source_arn = "${aws_sns_topic.concat.arn}"
}

#
# createPages Lambda Function
#
resource "aws_lambda_permission" "SNSLambdacreatePages" {
  statement_id = "SNSLambdacreatePages"
  action = "lambda:InvokeFunction"
  function_name = "${module.lambda-createPages.function_name}"
  principal = "sns.amazonaws.com"
  source_arn = "${aws_sns_topic.createPages.arn}"
}
#
# concatPages Lambda Function
#
resource "aws_lambda_permission" "SNSLambdaconcatPages" {
  statement_id = "SNSLambdaconcatPages"
  action = "lambda:InvokeFunction"
  function_name = "${module.lambda-concatPages.function_name}"
  principal = "sns.amazonaws.com"
  source_arn = "${aws_sns_topic.concatPages.arn}"
}
