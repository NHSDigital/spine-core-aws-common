import json

def lambda_handler(event, context):
    # TODO implement
    print(json.dumps(event))
    mailbox = event["mailbox"]

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": {
            "messageCount": 1,
            "messageList": [
                { "messageId": "12345", "mailbox": mailbox }
            ]
        }
    }
