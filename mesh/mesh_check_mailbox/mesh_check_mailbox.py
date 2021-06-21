"""
AWS Lambda function for checking MESH mailbox via API using standard MeshApiApplication
"""
from spinecore.mesh_api_application import MeshPollApplication

def lambda_handler(event, context):
    """
    Lambda Entrypoint, just use standard MeshPollApplication
    """
    return MeshPollApplication(event=event, context=context).main()
