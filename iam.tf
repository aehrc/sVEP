#
# Generic policy documents
#
data "aws_iam_policy_document" "main-apigateway" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]
    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

#
# queryVCF Lambda Function
#
data "aws_iam_policy_document" "lambda-queryVCF" {
  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]
    resources = [
      "${aws_dynamodb_table.datasets.arn}",
    ]
  }
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      "${aws_sns_topic.queryGTF.arn}",
      "${aws_sns_topic.queryVCFExtended.arn}",
      "${aws_sns_topic.concat.arn}",
    ]
  }
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = ["*"]
  }
}

#
# queryVCFExtended Lambda Function
#
data "aws_iam_policy_document" "lambda-queryVCFExtended" {
  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]
    resources = [
      "${aws_dynamodb_table.datasets.arn}",
    ]
  }
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      "${aws_sns_topic.queryGTF.arn}",
      "${aws_sns_topic.queryVCFExtended.arn}",
      "${aws_sns_topic.concat.arn}",
    ]
  }
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = ["*"]
  }
}


#
# queryGTF Lambda Function
#
data "aws_iam_policy_document" "lambda-queryGTF" {
  statement {
      actions = [
        "dynamodb:UpdateItem",
        "dynamodb:Query",
      ]
      resources = [
        "${aws_dynamodb_table.datasets.arn}",
      ]
  }
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      "${aws_sns_topic.pluginConsequence.arn}",
      "${aws_sns_topic.pluginUpdownstream.arn}",
    ]
  }
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = ["*"]
  }

}

#
# pluginConsequence Lambda Function
#
data "aws_iam_policy_document" "lambda-pluginConsequence" {

  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject",
    ]
    resources = ["*"]
  }

}

#
# pluginUpdownstream Lambda Function
#
data "aws_iam_policy_document" "lambda-pluginUpdownstream" {

  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject",
    ]
    resources = ["*"]
  }
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      "${aws_sns_topic.concat.arn}",
    ]
  }

}

#
# concat Lambda Function
#
data "aws_iam_policy_document" "lambda-concat" {
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
    ]
    resources = [
      "${aws_dynamodb_table.datasets.arn}",
    ]
  }
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject",
    ]
    resources = ["*"]
  }
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      "${aws_sns_topic.concat.arn}",
    ]
  }
}
