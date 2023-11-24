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

# TODO: Restrict the resources on these policies
#
# initQuery Lambda Function
#
data "aws_iam_policy_document" "lambda-initQuery" {
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      aws_sns_topic.concatStarter.arn,
      aws_sns_topic.queryVCF.arn,
    ]
  }
  statement {
    actions = [
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.svep-temp.arn}/*",
    ]
  }
  statement {
    actions = [
      "s3:GetObject",
    ]
    resources = ["*"]
  }
}

#
# queryVCF Lambda Function
#
data "aws_iam_policy_document" "lambda-queryVCF" {
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      aws_sns_topic.queryGTF.arn,
      aws_sns_topic.queryVCF.arn,
      aws_sns_topic.queryVCFsubmit.arn,
    ]
  }
  statement {
    actions = [
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.svep-temp.arn}/*",
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
# queryVCFsubmit Lambda Function
#
data "aws_iam_policy_document" "lambda-queryVCFsubmit" {
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      aws_sns_topic.queryGTF.arn,
    ]
  }
  statement {
    actions = [
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.svep-temp.arn}/*",
    ]
  }
}


#
# queryGTF Lambda Function
#
data "aws_iam_policy_document" "lambda-queryGTF" {
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      aws_sns_topic.pluginConsequence.arn,
      aws_sns_topic.pluginUpdownstream.arn,
      aws_sns_topic.queryGTF.arn,
    ]
  }
  statement {
    actions = [
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.svep-temp.arn}/*",
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
      "s3:DeleteObject",
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
      "s3:DeleteObject",
    ]
    resources = ["*"]
  }
}

#
# concat Lambda Function
#
data "aws_iam_policy_document" "lambda-concat" {
  statement {
    actions = [
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.svep-regions.arn,
    ]
  }
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      aws_sns_topic.createPages.arn,
    ]
  }
}

#
# concatStarter Lambda Function
#
data "aws_iam_policy_document" "lambda-concatStarter" {
  statement {
    actions = [
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.svep-regions.arn,
      aws_s3_bucket.svep-temp.arn,
    ]
  }
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      aws_sns_topic.concat.arn,
      aws_sns_topic.concatStarter.arn,
    ]
  }
}

#
# createPages Lambda Function
#
data "aws_iam_policy_document" "lambda-createPages" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["*"]
  }
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      aws_sns_topic.concatPages.arn,
      aws_sns_topic.createPages.arn,
    ]
  }
}

#
# concatPages Lambda Function
#
data "aws_iam_policy_document" "lambda-concatPages" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["*"]
  }
  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      aws_sns_topic.concatPages.arn,
    ]
  }
}

#
# getResultsURL Lambda Function
#
data "aws_iam_policy_document" "lambda-getResultsURL" {
  statement {
    actions = [
      "s3:GetObject",
    ]
    resources = ["*"]
  }
}
