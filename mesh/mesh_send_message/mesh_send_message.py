"""
AWS Lambda function for sending MESH message via API using standard MeshApiApplication
"""
from spinecore.mesh_api_application import MeshSendMessageApplication

def lambda_handler(event, context):
    """
    Lambda Entrypoint, just use standard MeshFetchMessageApplication
    """
    return MeshSendMessageApplication(event=event, context=context).main()
