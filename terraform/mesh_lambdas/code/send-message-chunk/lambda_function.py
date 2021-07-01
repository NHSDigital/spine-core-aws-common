import json

def lambda_handler(event, context):
    # TODO implement
    messageId = "09876"
    return {
        'statusCode': 200,
        'body': {
            "messageId": messageId,
            "isLastChunk": True
        }
    }
