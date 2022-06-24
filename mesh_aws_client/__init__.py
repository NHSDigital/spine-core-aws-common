"""
Module for common application functionality for MESH functions
"""
from mesh_aws_client.mesh_mailbox import MeshMailbox, MeshMessage
from mesh_aws_client.mesh_common import MeshMailbox as OldMeshMailbox
from mesh_aws_client.mesh_common import MeshMessage as OldMeshMessage


__all__ = ["MeshMailbox", "MeshMessage", "OldMeshMailbox", "OldMeshMessage"]
