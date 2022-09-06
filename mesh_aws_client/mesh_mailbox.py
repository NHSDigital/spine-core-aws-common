"""Mailbox class that handles all the complexity of talking to MESH API"""
import platform
import os
from typing import NamedTuple
from hashlib import sha256
import atexit
import datetime
import hmac
import tempfile
import uuid
import json
import requests

from spine_aws_common.logger import Logger
from mesh_aws_client.mesh_common import MeshCommon


class MeshMessage(NamedTuple):
    """Named tuple for holding Mesh Message info"""

    file_name: str = None
    data: any = None
    src_mailbox: str = None
    dest_mailbox: str = None
    workflow_id: str = None
    message_id: str = None
    will_compress: bool = False


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

    VERSION = "1.0.0"

    def __init__(self, log_object: Logger, mailbox: str, environment: str):
        self.mailbox = mailbox
        self.environment = environment
        self.temp_dir_object = None
        self.params = {}
        self.log_object = log_object
        self.client_cert_file = None
        self.client_key_file = None
        self.ca_cert_file = None
        self.maybe_verify_ssl = True
        self.dest_mailbox = None
        self.workflow_id = None

        self._setup()
        atexit.register(self.clean_up)

    def _setup(self) -> None:
        """Get mailbox config from SSM parameter store"""
        self.log_object.write_log(
            "MESHMBOX0001",
            None,
            {"mailbox": self.mailbox, "environment": self.environment},
        )

        common_params = MeshCommon.get_ssm_params(f"/{self.environment}/mesh")
        mailbox_params = MeshCommon.get_ssm_params(
            f"/{self.environment}/mesh/mailboxes/{self.mailbox}"
        )
        self.params = {**common_params, **mailbox_params}
        self.maybe_verify_ssl = (
            self.params.get(MeshMailbox.MESH_VERIFY_SSL, False) == "True"
        )
        self._write_certs_to_files()

    def clean_up(self) -> None:
        """Clear up after use"""
        if self.client_cert_file:
            filename = self.client_cert_file.name
            self.client_cert_file.close()
            os.remove(filename)
        if self.client_key_file:
            filename = self.client_key_file.name
            self.client_key_file.close()
            os.remove(filename)
        if self.ca_cert_file:
            filename = self.ca_cert_file.name
            self.ca_cert_file.close()
            os.remove(filename)

    def get_param(self, param) -> str:
        """Shortcut to get a parameter"""
        return self.params.get(param, None)

    def _write_certs_to_files(self) -> None:
        """Write the certificates to a local file"""
        self.log_object.write_log("MESHMBOX0002", None, None)

        # pylint: disable=consider-using-with
        self.temp_dir_object = tempfile.TemporaryDirectory()
        temp_dir = self.temp_dir_object.name

        # store as temporary files for the mesh client / requests library
        self.client_cert_file = tempfile.NamedTemporaryFile(dir=temp_dir, delete=False)
        client_cert = self.params[MeshMailbox.MESH_CLIENT_CERT]
        self.client_cert_file.write(client_cert.encode("utf-8"))
        self.client_cert_file.seek(0)

        self.client_key_file = tempfile.NamedTemporaryFile(dir=temp_dir, delete=False)
        client_key = self.params[MeshMailbox.MESH_CLIENT_KEY]
        self.client_key_file.write(client_key.encode("utf-8"))
        self.client_key_file.seek(0)

        self.ca_cert_file = None
        if self.maybe_verify_ssl:
            self.ca_cert_file = tempfile.NamedTemporaryFile(dir=temp_dir, delete=False)
            ca_cert = self.params[MeshMailbox.MESH_CA_CERT]
            self.ca_cert_file.write(ca_cert.encode("utf-8"))
            self.ca_cert_file.seek(0)
        # pylint: enable=consider-using-with

    def _build_mesh_authorization_header(
        self, nonce: str = None, noncecount: int = 0
    ) -> str:
        """Generate MESH Authorization header for mailbox"""
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
        header = (
            f"{self.AUTH_SCHEMA_NAME} {self.mailbox}:{nonce}:{str(noncecount)}:"
            + f"{timestamp}:{hash_code}"
        )
        self.log_object.write_log("MESHMBOX0003", None, {"header": header})
        return header

    def _default_headers(self):
        """
        Build standard headers including authorization
        """
        return {
            "Authorization": self._build_mesh_authorization_header(),
        }

    def _setup_session(self) -> requests.Session:
        session = requests.Session()
        session.headers = self._default_headers()
        if self.maybe_verify_ssl:
            session.verify = self.ca_cert_file.name
        else:
            session.verify = False
        session.cert = (self.client_cert_file.name, self.client_key_file.name)
        return session

    def set_destination_and_workflow(self, dest_mailbox, workflow_id) -> None:
        """Set destination mailbox and workflow_id"""
        self.dest_mailbox = dest_mailbox
        self.workflow_id = workflow_id

    def handshake(self) -> int:
        """
        Do an authenticated handshake with the MESH server
        """
        session = self._setup_session()
        session.headers[
            "Mex-ClientVersion"
        ] = f"AWS Serverless MESH Client={MeshMailbox.VERSION}"
        session.headers["Mex-OSArchitecture"] = platform.machine()
        session.headers["Mex-OSName"] = platform.system()
        session.headers["Mex-OSVersion"] = platform.release()

        mesh_url = self.params[MeshMailbox.MESH_URL]
        url = f"{mesh_url}/messageexchange/{self.mailbox}"
        response = session.get(url)
        self.log_object.write_log(
            "MESHMBOX0004", None, {"http_status": response.status_code}
        )
        return response.status_code

    def authenticate(self) -> int:
        """
        Povided for compatibility
        """
        return self.handshake()

    def send_chunk(
        self,
        mesh_message_object: MeshMessage,
        number_of_chunks: int = 1,
        chunk_num: int = 1,
    ):
        """Send a chunk from a stream"""
        # override mailbox dest_mailbox if provided in message_object
        session = self._setup_session()
        session.headers["Mex-From"] = mesh_message_object.src_mailbox
        session.headers["Mex-To"] = mesh_message_object.dest_mailbox
        session.headers["Mex-WorkflowID"] = mesh_message_object.workflow_id
        session.headers["Mex-FileName"] = mesh_message_object.file_name
        session.headers["Mex-Chunk-Range"] = f"{chunk_num}:{number_of_chunks}"
        session.headers["Content-Type"] = "application/octet-stream"
        session.headers["Mex-Content-Encrypted"] = "N"
        if mesh_message_object.will_compress:
            session.headers["Content-Encoding"] = "gzip"
            session.headers["Mex-Content-Compress"] = "Y"
            session.headers["Mex-Content-Compressed"] = "Y"

        mesh_url = self.params[MeshMailbox.MESH_URL]
        if chunk_num == 1:
            session.headers["Mex-MessageType"] = "DATA"
            url = f"{mesh_url}/messageexchange/{self.mailbox}/outbox"
        else:
            url = (
                f"{mesh_url}/messageexchange/{self.mailbox}/outbox/"
                + f"{mesh_message_object.message_id}/{chunk_num}"
            )
        response = session.post(url, data=mesh_message_object.data, stream=True)
        response.raise_for_status()
        response.raw.decode_content = True
        message_id = json.loads(response.text)["messageID"]
        self.log_object.write_log(
            "MESHSEND0007",
            None,
            {
                "file": mesh_message_object.file_name,
                "http_status": response.status_code,
                "message_id": message_id,
            },
        )
        return response

    def get_chunk(self, message_id, chunk_num=1):
        """Return a response object for a MESH chunk"""
        session = self._setup_session()
        mesh_url = self.params[MeshMailbox.MESH_URL]

        # if chunk number = 1, get first part
        if chunk_num == 1:
            url = f"{mesh_url}/messageexchange/{self.mailbox}/inbox/{message_id}"
        else:
            url = (
                f"{mesh_url}/messageexchange/{self.mailbox}/inbox/{message_id}"
                + f"/{chunk_num}"
            )
        response = session.get(url, stream=True, headers={"Accept-Encoding": "gzip"})
        response.raw.decode_content = True
        return response

    def list_messages(self):
        """Return a list of messages in the mailbox in the form:
        [
            '20220610195418651944_2202CC',
            '20220613142621549393_6430C9'
        ]
        """
        session = self._setup_session()
        mesh_url = self.params[MeshMailbox.MESH_URL]
        url = f"{mesh_url}/messageexchange/{self.mailbox}/inbox"
        response = session.get(url)
        response.raise_for_status()

        response_data = json.loads(response.text)
        message_ids = response_data["messages"]
        self.log_object.write_log(
            "MESHMBOX0005",
            None,
            {
                "mailbox": self.mailbox,
                "message_count": len(message_ids),
                "http_status": response.status_code,
            },
        )
        return response, message_ids

    def acknowledge_message(self, message_id):
        """
        Acknowledge receipt of the last message from the mailbox.
        """
        session = self._setup_session()
        mesh_url = self.params[MeshMailbox.MESH_URL]
        url = (
            f"{mesh_url}/messageexchange/{self.mailbox}/inbox/{message_id}"
            f"/status/acknowledged"
        )
        response = session.put(url)
        self.log_object.write_log(
            "MESHMBOX0006",
            None,
            {"message_id": message_id, "http_status": response.status_code},
        )
        return response
