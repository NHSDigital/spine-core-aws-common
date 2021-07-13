"""Mailbox class that handles all the complexity of talking to MESH API"""
from collections import namedtuple
import os
import hmac
from mesh_aws_client.mesh_common import MeshCommon
import uuid
import datetime
from hashlib import sha256
import tempfile
import atexit

# from http import HTTPStatus
import requests
from urllib3.exceptions import InsecureRequestWarning
import boto3
from spine_aws_common.logger import Logger


class MeshMailbox:  # pylint: disable=too-many-instance-attributes
    """Mailbox class that handles all the complexity of talking to MESH API"""

    AUTH_SCHEMA_NAME = "NHSMESH"

    MESH_CA_CERT = "MESH_CA_CERT"
    MESH_CLIENT_CERT = "MESH_CLIENT_CERT"
    MESH_CLIENT_KEY = "MESH_CLIENT_KEY"
    MESH_SHARED_KEY = "MESH_SHARED_KEY"
    MESH_URL = "MESH_URL"
    MESH_VERIFY_SSL = "MESH_VERIFY_SSL"
    MAILBOX_PASSWORD = "MAILBOX_PASSWORD"
    INBOUND_BUCKET = "INBOUND_BUCKET"
    INBOUND_FOLDER = "INBOUND_FOLDER"
    ALLOWED_SENDERS = "ALLOWED_SENDERS"
    ALLOWED_RECIPIENTS = "ALLOWED_RECIPIENTS"
    ALLOWED_WORKFLOW_IDS = "ALLOWED_WORKFLOW_IDS"

    def __init__(self, log_object: Logger, environment: str, mailbox):
        self.mailbox = mailbox
        self.environment = environment
        self.temp_dir_object = None
        self.params = {}
        self.log_object = log_object
        self.client_cert_file = None
        self.client_key_file = None
        self.ca_cert_file = None
        self._setup()
        atexit.register(self._clean_up)

    def _setup(self):
        """Get mailbox config from SSM paramater store"""
        self.log_object.write_log(
            "MESH0001", None, {"mailbox": self.mailbox, "environment": self.environment}
        )

        common_params = MeshCommon.get_ssm_params(f"/{self.environment}/mesh")
        mailbox_params = MeshCommon.get_ssm_params(
            f"/{self.environment}/mesh/mailboxes/{self.mailbox}"
        )
        self.params = {**common_params, **mailbox_params}
        # self._write_certs_to_files()

        # maybe_verify = bool(
        #     self.mailbox_params.get("MESH_VERIFY_SSL", "True") == "True"
        # )

        # if not maybe_verify:
        #     requests.urllib3.disable_warnings(InsecureRequestWarning)

        # # rewrite MeshClient
        # self.mesh_client = ExtendedMeshClient(
        #     common_params["MESH_URL"],
        #     self.mailbox,
        #     mailbox_params["MAILBOX_PASSWORD"],
        #     shared_key=common_params["MESH_SHARED_KEY"].encode("utf8"),
        #     cert=(self.client_cert_file.name, self.client_key_file.name),
        #     verify=self.ca_cert_file.name if maybe_verify else None,
        #     max_chunk_size=MeshCommon.DEFAULT_CHUNK_SIZE,
        # )

    def _clean_up(self):
        """Clear up after use"""

    def get_param(self, param):
        """Shortcut to get a parameter"""
        return self.params.get(param, None)

    def _write_certs_to_files(self):
        """Write the certificates to a local file"""
        # pylint: disable=consider-using-with
        self.temp_dir_object = tempfile.TemporaryDirectory()
        temp_dir = self.temp_dir_object.name

        # store as temporary files for the mesh client
        self.client_cert_file = tempfile.NamedTemporaryFile(dir=temp_dir, delete=False)
        client_cert = self.params[MeshMailbox.MESH_CLIENT_CERT]
        self.client_cert_file.write(client_cert.encode("utf-8"))
        self.client_cert_file.seek(0)

        self.client_key_file = tempfile.NamedTemporaryFile(dir=temp_dir, delete=False)
        client_key = self.params[MeshMailbox.MESH_CLIENT_KEY]
        self.client_key_file.write(client_key.encode("utf-8"))
        self.client_key_file.seek(0)

        self.ca_cert_file = None
        if self.params.get("MESH_VERIFY_SSL", False) == "True":
            self.ca_cert_file = tempfile.NamedTemporaryFile(dir=temp_dir, delete=False)
            ca_cert = self.params[MeshMailbox.MESH_CA_CERT]
            self.ca_cert_file.write(ca_cert.encode("utf-8"))
            self.ca_cert_file.seek(0)
        # pylint: enable=consider-using-with

    def _build_mesh_authorization_header(
        self,
        nonce: str = None,
        noncecount: int = 0,
    ):
        """Generate MESH Authorization header for mailboxid."""
        if not nonce:
            nonce = str(uuid.uuid4())
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")

        # e.g. NHSMESH AMP01HC001:bd0e2bd5-218e-41d0-83a9-73fdec414803:0:202005041305
        hmac_msg = (
            f"{self.mailbox}:{nonce}:{str(noncecount)}:"
            + f"{self.params[MeshMailbox.MAILBOX_PASSWORD]}:{timestamp}"
        )

        hash_code = hmac.HMAC(
            self.params[MeshMailbox.MESH_SHARED_KEY].encode(),
            hmac_msg.encode(),
            sha256,
        ).hexdigest()
        return (
            f"{self.AUTH_SCHEMA_NAME} {self.mailbox}:{nonce}:{str(noncecount)}:"
            + f"{timestamp}:{hash_code}"
        )
