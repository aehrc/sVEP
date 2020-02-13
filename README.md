# Serverless VEP

## Why serverless?
Serverless means the service does not require any servers to be provisioned. The
idea is to minimise running costs, as well as support arbitrary scalablility. It
also means setup is very fast.

## Installation
Install using `terraform init` to pull the module, followed by running
Running `terraform apply` will create the infrastucture.
For adding data to the beacon, see the API.

To shut down the entire service run `terraform destroy`. Any created datasets
will be lost (but not the VCFs on which they are based).

For standalone use the aws provider will need to be added in main.tf. See the
example for more information.

## Known Issues
##### Cannot run sVEP without creating a reference S3 bucket - should be fixed soon
##### Initial sVEP version doesnt support structural variants and regulatory regions
##### Concat function is still in the development phase
