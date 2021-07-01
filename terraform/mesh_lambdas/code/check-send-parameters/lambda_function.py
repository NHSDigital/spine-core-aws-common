import json

def lambda_handler(event, context):
    # TODO implement
    print(json.dumps(event))

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": {
            "srcMailbox": "X",
            "destMailbox": "Y",
            "workflowId": "Z",
            "chunk": False,
            "chunkNumber": 1,
            "complete": False
        },
        "context": json.dumps(context)
    }
