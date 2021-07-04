"""Common methods and classes used for mesh client"""
# from io import BytesIO
import os
import tempfile
import atexit
import requests
from urllib3.exceptions import InsecureRequestWarning
import boto3
from mesh_client import MeshClient


class SingletonCheckFailure(Exception):
    """Singleton check failed"""

    def __init__(self, msg=None):
        super().__init__()
        if msg:
            self.msg = msg


class MeshCommon:  # pylint: disable=too-few-public-methods
    """Common"""

    MIB = 1024 * 1024
    DEFAULT_CHUNK_SIZE = 20 * MIB


class ExtendedMeshClient(MeshClient):
    """Extended functionality for lambda send"""


class MeshMailbox:
    """Mesh mailbox object, gets parameters from SSM Parameter Store"""

    def __init__(self, mailbox, environment="default", ssm_client=None):
        self.mailbox = mailbox
        self.common_params = None
        self.mailbox_params = None
        self.ca_cert_file = None
        self.client_cert_file = None
        self.client_key_file = None
        self.environment = environment
        self.dest_mailbox = None
        self.workflow_id = None
        self.ssm_client = ssm_client
        self._setup()
        atexit.register(self.clean_up)

    def clean_up(self):
        """Close mesh client at exit"""
        self.mesh_client.close()

    def _setup(self):
        """Get the parameters from SSM paramter store"""
        # TODO refactor
        if not self.ssm_client:
            self.ssm_client = boto3.client("ssm")
        print(f"Getting common params from /{self.environment}/mesh")
        common_params_result = self.ssm_client.get_parameters_by_path(
            Path=f"/{self.environment}/mesh", Recursive=False, WithDecryption=True
        )
        self.common_params = self._convert_params_to_dict(
            common_params_result.get("Parameters", {})
        )
        print(
            f"Getting mailbox params from /{self.environment}"
            + f"/mesh/mailboxes/{self.mailbox}"
        )
        mailbox_params_result = self.ssm_client.get_parameters_by_path(
            Path=f"/{self.environment}/mesh/mailboxes/{self.mailbox}",
            Recursive=False,
            WithDecryption=True,
        )
        self.mailbox_params = self._convert_params_to_dict(
            mailbox_params_result.get("Parameters", {})
        )
        self._write_certs_to_files()

        if self.common_params.get("MESH_VERIFY_SSL", "False") != "True":
            requests.urllib3.disable_warnings(InsecureRequestWarning)
        self.mesh_client = ExtendedMeshClient(
            self.common_params["MESH_URL"],
            self.mailbox,
            self.mailbox_params["MESH_MAILBOX_PASSWORD"],
            shared_key=self.common_params["MESH_SHARED_KEY"].encode("utf8"),
            cert=(  # self.client_cert_file, self.client_key_file),
                "/tmp/client-sha2.crt",
                "/tmp/client-sha2.key",
            ),
            verify=None,  # self.ca_cert_file,
            max_chunk_size=MeshCommon.DEFAULT_CHUNK_SIZE,
        )

    @staticmethod
    def _convert_params_to_dict(params):
        """Convert paramater dict to key:value dict"""
        new_dict = {}
        for entry in params:
            name = entry.get("Name", None)
            if name:
                var_name = os.path.basename(name)
                new_dict[var_name] = entry.get("Value", None)
        return new_dict

    def get_common_parameters(self):
        """Getter"""
        return self.common_params

    def get_mailbox_parameters(self):
        """Getter"""
        return self.mailbox_params

    def _write_certs_to_files(self):
        """Write the certificates to a local file"""
        temp_dir_object = tempfile.TemporaryDirectory()
        temp_dir = temp_dir_object.name
        self.client_cert_file = ""
        self.client_key_file = ""
        # store as temporary files for the mesh client
        with tempfile.NamedTemporaryFile(
            dir=temp_dir, delete=False
        ) as client_cert_file:
            client_cert = self.common_params["MESH_CLIENT_CERT"]
            client_cert_file.write(client_cert.encode("utf-8"))
            self.client_cert_file = client_cert_file.name
        with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False) as client_key_file:
            client_key = self.common_params["MESH_CLIENT_KEY"]
            client_key_file.write(client_key.encode("utf-8"))
            self.client_key_file = client_key_file.name

        self.ca_cert_file = None
        if self.common_params.get("MESH_VERIFY_SSL", False) == "True":
            with tempfile.NamedTemporaryFile(
                dir=temp_dir, delete=False
            ) as ca_cert_file:
                ca_cert = self.common_params["MESH_CA_CERT"]
                ca_cert_file.write(ca_cert.encode("utf-8"))
                self.ca_cert_file = ca_cert_file.name

    def set_destination_and_workflow(self, dest_mailbox, workflow_id):
        """Set destination mailbox and workflow_id"""
        self.dest_mailbox = dest_mailbox
        self.workflow_id = workflow_id

    def authenticate(self):
        """Authenticate to MESH mailbox"""
        return self.mesh_client.handshake()

    def send_chunk(  # pylint: disable=too-many-arguments
        self,
        message_id=None,
        file_name=None,
        chunk=False,
        chunk_size=MeshCommon.DEFAULT_CHUNK_SIZE,
        chunk_num=1,
        data=None,
    ):
        """Send a chunk"""
        print("Sending ")
        if not chunk:
            message_id = self.mesh_client.send_message(
                self.dest_mailbox,
                workflow_id=self.workflow_id,
                filename=file_name,
                data=data,
            )
        else:
            # TODO chunking is more interesting, as mesh_client doesn't have a
            # function for sending one chunk only
            offset = chunk_size * chunk_num
            print(f"Calculated offset is {offset}")
        return (200, message_id)

    def get_chunk(
        self, message_id, chunk_size=MeshCommon.DEFAULT_CHUNK_SIZE, chunk_num=1
    ):
        """Get a chunk"""
