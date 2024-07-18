#
# API Gateway
#
resource "aws_api_gateway_rest_api" "VPApi" {
  name = "VPApi"
  description = "API That implements the Variant Prioritization specification"
}

# 
# /submit
# 
resource "aws_api_gateway_resource" "submit" {
  rest_api_id = aws_api_gateway_rest_api.VPApi.id
  parent_id = aws_api_gateway_rest_api.VPApi.root_resource_id
  path_part = "submit"
}

resource "aws_api_gateway_method" "submit-options" {
  rest_api_id = aws_api_gateway_rest_api.VPApi.id
  resource_id = aws_api_gateway_resource.submit.id
  http_method = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "submit-options" {
  rest_api_id = aws_api_gateway_method.submit-options.rest_api_id
  resource_id = aws_api_gateway_method.submit-options.resource_id
  http_method = aws_api_gateway_method.submit-options.http_method
  status_code = "200"

  response_parameters ={
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models ={
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration" "submit-options" {
  rest_api_id = aws_api_gateway_method.submit-options.rest_api_id
  resource_id = aws_api_gateway_method.submit-options.resource_id
  http_method = aws_api_gateway_method.submit-options.http_method
  type = "MOCK"

  request_templates ={
    "application/json" = <<TEMPLATE
      {
        "statusCode": 200
      }
    TEMPLATE
  }
}

resource "aws_api_gateway_integration_response" "submit-options" {
  rest_api_id = aws_api_gateway_method.submit-options.rest_api_id
  resource_id = aws_api_gateway_method.submit-options.resource_id
  http_method = aws_api_gateway_method.submit-options.http_method
  status_code = aws_api_gateway_method_response.submit-options.status_code

  response_parameters ={
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,PATCH,POST'"
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  response_templates ={
    "application/json" = ""
  }

  depends_on = [aws_api_gateway_integration.submit-options]
}

resource "aws_api_gateway_method" "submit-patch" {
  rest_api_id = aws_api_gateway_rest_api.VPApi.id
  resource_id = aws_api_gateway_resource.submit.id
  http_method = "PATCH"
  authorization = "NONE"

}

resource "aws_api_gateway_method_response" "submit-patch" {
  rest_api_id = aws_api_gateway_method.submit-patch.rest_api_id
  resource_id = aws_api_gateway_method.submit-patch.resource_id
  http_method = aws_api_gateway_method.submit-patch.http_method
  status_code = "200"

  response_parameters ={
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models ={
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration" "submit-patch" {
  rest_api_id = aws_api_gateway_method.submit-patch.rest_api_id
  resource_id = aws_api_gateway_method.submit-patch.resource_id
  http_method = aws_api_gateway_method.submit-patch.http_method
  type = "AWS_PROXY"
  uri = module.lambda-initQuery.function_invoke_arn
  integration_http_method = "POST"
}

resource "aws_api_gateway_integration_response" "submit-patch" {
  rest_api_id = aws_api_gateway_method.submit-patch.rest_api_id
  resource_id = aws_api_gateway_method.submit-patch.resource_id
  http_method = aws_api_gateway_method.submit-patch.http_method
  status_code = aws_api_gateway_method_response.submit-patch.status_code

  response_templates ={
    "application/json" = ""
  }

  depends_on = [aws_api_gateway_integration.submit-patch]
}

resource "aws_api_gateway_method" "submit-post" {
  rest_api_id = aws_api_gateway_rest_api.VPApi.id
  resource_id = aws_api_gateway_resource.submit.id
  http_method = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "submit-post" {
  rest_api_id = aws_api_gateway_method.submit-post.rest_api_id
  resource_id = aws_api_gateway_method.submit-post.resource_id
  http_method = aws_api_gateway_method.submit-post.http_method
  status_code = "200"

  response_parameters ={
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models ={
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration" "submit-post" {
  rest_api_id = aws_api_gateway_method.submit-post.rest_api_id
  resource_id = aws_api_gateway_method.submit-post.resource_id
  http_method = aws_api_gateway_method.submit-post.http_method
  type = "AWS_PROXY"
  uri = module.lambda-initQuery.function_invoke_arn
  integration_http_method = "POST"
}

resource "aws_api_gateway_integration_response" "submit-post" {
  rest_api_id = aws_api_gateway_method.submit-post.rest_api_id
  resource_id = aws_api_gateway_method.submit-post.resource_id
  http_method = aws_api_gateway_method.submit-post.http_method
  status_code = aws_api_gateway_method_response.submit-post.status_code

  response_templates ={
    "application/json" = ""
  }

  depends_on = [aws_api_gateway_integration.submit-post]
}

# 
# /results_url
# 
resource "aws_api_gateway_resource" "results-url" {
  rest_api_id = aws_api_gateway_rest_api.VPApi.id
  parent_id = aws_api_gateway_rest_api.VPApi.root_resource_id
  path_part = "results_url"
}

resource "aws_api_gateway_method" "results-url-options" {
  rest_api_id = aws_api_gateway_rest_api.VPApi.id
  resource_id = aws_api_gateway_resource.results-url.id
  http_method = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "results-url-options" {
  rest_api_id = aws_api_gateway_method.results-url-options.rest_api_id
  resource_id = aws_api_gateway_method.results-url-options.resource_id
  http_method = aws_api_gateway_method.results-url-options.http_method
  status_code = "200"

  response_parameters ={
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models ={
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration" "results-url-options" {
  rest_api_id = aws_api_gateway_method.results-url-options.rest_api_id
  resource_id = aws_api_gateway_method.results-url-options.resource_id
  http_method = aws_api_gateway_method.results-url-options.http_method
  type = "MOCK"

  request_templates ={
    "application/json" = <<TEMPLATE
      {
        "statusCode": 200
      }
    TEMPLATE
  }
}

resource "aws_api_gateway_integration_response" "results-url-options" {
  rest_api_id = aws_api_gateway_method.results-url-options.rest_api_id
  resource_id = aws_api_gateway_method.results-url-options.resource_id
  http_method = aws_api_gateway_method.results-url-options.http_method
  status_code = aws_api_gateway_method_response.results-url-options.status_code

  response_parameters ={
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,GET'"
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  response_templates ={
    "application/json" = ""
  }

  depends_on = [aws_api_gateway_integration.results-url-options]
}

resource "aws_api_gateway_method" "results-url-get" {
  rest_api_id = aws_api_gateway_rest_api.VPApi.id
  resource_id = aws_api_gateway_resource.results-url.id
  http_method = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "results-url-get" {
  rest_api_id = aws_api_gateway_method.results-url-get.rest_api_id
  resource_id = aws_api_gateway_method.results-url-get.resource_id
  http_method = aws_api_gateway_method.results-url-get.http_method
  status_code = "200"

  response_parameters ={
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models ={
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration" "results-url-get" {
  rest_api_id = aws_api_gateway_method.results-url-get.rest_api_id
  resource_id = aws_api_gateway_method.results-url-get.resource_id
  http_method = aws_api_gateway_method.results-url-get.http_method
  type = "AWS_PROXY"
  uri = module.lambda-getResultsURL.function_invoke_arn
  integration_http_method = "POST"
}

resource "aws_api_gateway_integration_response" "results-url-get" {
  rest_api_id = aws_api_gateway_method.results-url-get.rest_api_id
  resource_id = aws_api_gateway_method.results-url-get.resource_id
  http_method = aws_api_gateway_method.results-url-get.http_method
  status_code = aws_api_gateway_method_response.results-url-get.status_code

  response_templates ={
    "application/json" = ""
  }

  depends_on = [aws_api_gateway_integration.results-url-get]
}

#
# Deployment
#
resource "aws_api_gateway_deployment" "VPApi" {
  rest_api_id = aws_api_gateway_rest_api.VPApi.id
  stage_name  = "dev"
  # taint deployment if any api resources change
  stage_description = md5(join("", [
    md5(file("${path.module}/api.tf")),
    # /submit
    aws_api_gateway_method.submit-options.id,
    aws_api_gateway_integration.submit-options.id,
    aws_api_gateway_integration_response.submit-options.id,
    aws_api_gateway_method_response.submit-options.id,
    aws_api_gateway_method.submit-patch.id,
    aws_api_gateway_integration.submit-patch.id,
    aws_api_gateway_integration_response.submit-patch.id,
    aws_api_gateway_method_response.submit-patch.id,
    aws_api_gateway_method.submit-post.id,
    aws_api_gateway_integration.submit-post.id,
    aws_api_gateway_integration_response.submit-post.id,
    aws_api_gateway_method_response.submit-post.id,
    # /results_url
    aws_api_gateway_method.results-url-options.id,
    aws_api_gateway_integration.results-url-options.id,
    aws_api_gateway_integration_response.results-url-options.id,
    aws_api_gateway_method_response.results-url-options.id,
    aws_api_gateway_method.results-url-get.id,
    aws_api_gateway_integration.results-url-get.id,
    aws_api_gateway_integration_response.results-url-get.id,
    aws_api_gateway_method_response.results-url-get.id,
  ]))
}
