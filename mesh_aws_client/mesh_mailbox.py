"""Mailbox class that handles all the complexity of talking to MESH API"""
from io import BytesIO
import platform
from http import HTTPStatus
from typing import NamedTuple
from hashlib import sha256
import atexit
import datetime
import hmac
import tempfile
import uuid
import requests
import json

from spine_aws_common.logger import Logger
from .mesh_common import MeshCommon


class MeshMessage(NamedTuple):
    """Named tuple for holding Mesh Message info"""

    data_stream: BytesIO = None
    src_mailbox: str = None
    dest_mailbox: str = None
    workflow_id: str = None
    message_id: str = None


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

    VERSION = "0.0.2"

    def __init__(self, log_object: Logger, environment: str, mailbox: str):
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
        atexit.register(self._clean_up)

    def _setup(self) -> None:
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

        self.maybe_verify_ssl = (
            self.params.get(MeshMailbox.MESH_VERIFY_SSL, False) == "True"
        )
        self._write_certs_to_files()

    def _clean_up(self) -> None:
        """Clear up after use"""

    def get_param(self, param) -> str:
        """Shortcut to get a parameter"""
        return self.params.get(param, None)

    def _write_certs_to_files(self) -> None:
        """Write the certificates to a local file"""
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
        return (
            f"{self.AUTH_SCHEMA_NAME} {self.mailbox}:{nonce}:{str(noncecount)}:"
            + f"{timestamp}:{hash_code}"
        )

    def _default_headers(self):
        """
        Build standard headers including authorization
        """
        return {
            "Authorization": self._build_mesh_authorization_header(),
            "Mex-ClientVersion": f"AWS Serverless MESH Client={MeshMailbox.VERSION}",
            "Mex-OSArchitecture": platform.machine(),
            "Mex-OSName": platform.system(),
            "Mex-OSVersion": platform.release(),
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
        mesh_url = self.params[MeshMailbox.MESH_URL]
        url = f"{mesh_url}/messageexchange/{self.mailbox}"
        response = session.get(url)

        return response.status_code

    def authenticate(self) -> int:
        """
        Povided for compatibility
        """
        return self.handshake()

    def send_chunk_stream(
        self,
        mesh_message_object: MeshMessage,
        chunk: bool = False,
        chunk_size: int = MeshCommon.DEFAULT_CHUNK_SIZE,
        chunk_num: int = 1,
    ):
        """Send a chunk from a stream"""
        # override mailbox dest_mailbox if provided in message_object
        return HTTPStatus.NOT_IMPLEMENTED.value

    def get_chunk(self, message_id, chunk_num=1):
        """Return a response object for a MESH chunk"""
        session = self._setup_session()
        mesh_url = self.params[MeshMailbox.MESH_URL]

        # if chunk number = 1, get first part
        url = f"{mesh_url}/messageexchange/{self.mailbox}/inbox/{message_id}"
        # otherwise get nth part

        response = session.get(url, stream=True)
        response.raw.decode_content = True
        return response

    def list_messages(self):
        """PCRM-6130 Return a list of messages in the mailbox in the form:
        [
            '20220610195418651944_2202CC',
            '20220613142621549393_6430C9'
        ]
        """
        session = self._setup_session()
        mesh_url = self.params[MeshMailbox.MESH_URL]
        url = f"{mesh_url}/messageexchange/{self.mailbox}/inbox"
        response = session.get(url)

        text_dict = response.text
        python_dict = json.loads(text_dict)
        python_list = python_dict['messages']
        return python_list

    def acknowledge_message(self, message_id):
        """
        PCRM-6130 Acknowledge receipt of the last message from the mailbox.
        """
        session = self._setup_session()
        mesh_url = self.params[MeshMailbox.MESH_URL]
        url = f"{mesh_url}/messageexchange/{self.mailbox}/inbox/{message_id}/status/bc"
        response = session.put(url)
        return response.status_code