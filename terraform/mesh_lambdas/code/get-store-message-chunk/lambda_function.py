import json

def lambda_handler(event, context):
    # TODO implement
    messageId = event["messageId"]
    return {
        'statusCode': 200,
        'body': {
            "messageId": messageId,
            "isLastChunk": True
        }
    }
