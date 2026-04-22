from enum import Enum


class ResourceType(Enum):
    """CDK Linter (CFN part) only supports resource types listed here"""

    # values map to CFN type strings
    DDB = "AWS::DynamoDB::Table"
    S3 = "AWS::S3::Bucket"
    SQS = "AWS::SQS::Queue"
    LAMBDA = "AWS::Lambda::Function"
    ROLE = "AWS::IAM::Role"
    POLICY = "AWS::IAM::Policy"
