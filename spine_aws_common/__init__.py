"""
Module for common application functionality for Lambda functions
"""
from spine_aws_common.lambda_application import LambdaApplication
from spine_aws_common.batch_application import BatchApplication
from spine_aws_common.api_gateway_application import APIGatewayApplication
from spine_aws_common.api_gateway_v2_application import APIGatewayV2Application
from spine_aws_common.alb_application import ALBApplication
from spine_aws_common.dynamodb_streams_application import DynamoDBStreamsApplication
from spine_aws_common.eventbridge_application import EventbridgeApplication
from spine_aws_common.kinesis_stream_application import KinesisStreamApplication
from spine_aws_common.s3_event_application import S3EventApplication
from spine_aws_common.s3_object_event_application import S3ObjectEventApplication
from spine_aws_common.ses_application import SESApplication
from spine_aws_common.sns_application import SNSApplication
from spine_aws_common.sqs_application import SQSApplication

__all__ = [
    "LambdaApplication",
    "BatchApplication",
    "APIGatewayApplication",
    "APIGatewayV2Application",
    "ALBApplication",
    "DynamoDBStreamsApplication",
    "EventbridgeApplication",
    "KinesisStreamApplication",
    "S3EventApplication",
    "S3ObjectEventApplication",
    "SESApplication",
    "SNSApplication",
    "SQSApplication",
]
