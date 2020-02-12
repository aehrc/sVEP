output "api_url" {
  value = "${aws_api_gateway_deployment.VPApi.invoke_url}"
  description = "URL used to invoke the API."
}
