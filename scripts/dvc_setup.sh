#!/bin/bash

set -eux

source .env

uv run dvc remote add ${S3_BUCKET} s3://${S3_BUCKET}/dvcstore
uv run dvc remote default ${S3_BUCKET}

uv run dvc remote modify ${S3_BUCKET} endpointurl  ${S3_ENDPOINT}

uv run dvc remote modify --local ${S3_BUCKET} access_key_id ${S3_ACCESS_KEY}
uv run dvc remote modify --local ${S3_BUCKET} secret_access_key ${S3_SECRET_KEY}
