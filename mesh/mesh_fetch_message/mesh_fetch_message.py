"""
AWS Lambda function for fetching MESH message via API using standard MeshApiApplication
"""
from spinecore.mesh_api_application import MeshFetchMessageApplication


def lambda_handler(event, context):
    """
    Lambda Entrypoint, just use standard MeshFetchMessageApplication
    """
    return MeshFetchMessageApplication(event=event, context=context).main()
