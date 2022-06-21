""" Testing the mailbox functionality, including chunking and streaming """
from unittest import mock
from moto import mock_s3, mock_ssm
import gzip
import boto3
from spine_aws_common.logger import Logger

from mesh_aws_client.tests.mesh_testing_common import MeshTestCase, MeshTestingCommon
from mesh_aws_client import (
    MeshMailbox,
    OldMeshMailbox,
    OldMeshMessage
)

from mesh_aws_client.mesh_fetch_message_chunk_application import (
    MeshFetchMessageChunkApplication,
)


class LocalRealDevMeshMailboxTest(MeshTestCase):
    """
    Tests for mailbox functionality against real local dev Spine MESH
    for developing locally with a local Spine VM
    """

    MESH_URL = "https://192.168.247.130"

    CLIENT_CERT = """-----BEGIN CERTIFICATE-----
MIIEUDCCAjgCAQIwDQYJKoZIhvcNAQELBQAwbDELMAkGA1UEBhMCVUsxFzAVBgNV
BAgMDldlc3QgWW9ya3NoaXJlMQ4wDAYDVQQHDAVMZWVkczEMMAoGA1UECgwDTkhT
MQ4wDAYDVQQLDAVIU0NJQzEWMBQGA1UEAwwNQ0EuY2ZoLm5ocy51azAeFw0yMDA0
MTYxODAyNDJaFw0zMDA0MTQxODAyNDJaMHAxCzAJBgNVBAYTAlVLMRcwFQYDVQQI
DA5XZXN0IFlvcmtzaGlyZTEOMAwGA1UEBwwFTGVlZHMxDDAKBgNVBAoMA25oczEQ
MA4GA1UECwwHRGV2aWNlczEYMBYGA1UEAwwPVEVTVC5jZmgubmhzLnVrMIIBIjAN
BgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Hl48oikTUeMsHHHfPeF2VEHnppp
izWmc1781sfVO0MA6eEudgEOfy3mF/nJGjEiMmlhmYjr8LZribpHqKHJSZX3NkYd
oWN8UrS7ryZtR5I0q5sD/wYhPgbAhOkUvMOARM+XJ8+Fv8cJnQUShoFz18QrTpRR
djWV/8e9Sv6JaSZenurVf8kk7nLvNB3GpnvL76p1GeOy04+WoI4x1mZx8MODsUFn
v+wLU8ORDnXLysOkGz6atI56bXqLJYfnfUhTX3C0YbiTV5uOGkVQZ9LDJP23uSpq
YQ/TXRSJ2MjbdwDBYZxabJ0MTBDXaJqUx8g8HKZpmyulAuKsn5r/ewmEbwIDAQAB
MA0GCSqGSIb3DQEBCwUAA4ICAQBwMB5Pxbh8eyW7bpKrm+B4SP9crHnaoh0HVsxc
NcojybP882+VpKisc3hEGy3HcjRPGVUOoDb/Rnogwwan0hX8AzbayTroaTQTsM9I
tlCGewA5tdKmX1wWtwoQKjLsX7r/luHyLnJnig3x8DewdmN4P16Pw4/0yo5oQy/m
MwNKiutRSWST/XZfE+s1fcwFAO3hHYkFrgRdn1AZV6H0iCwEPcDoxHCtEjSThugx
vmPMpHDMuqqvviGV6ZKR3kDUD87bicnr16kBxm5BBGqvsYOvMfFL1c0IizMMMm4v
kCSuVEIjBZuxn/E7NGYejzG2RHGMYhNJ+qUBWLS7/ejpjLZpXDn4GT+DeEjLWVB3
SnJuOzHveho3C2VxCeDBNDLJa24MXMQZ1RgjaliG4BzBLcj7mj0QShwq5ZSmyxG4
jXCLtGuu6QXKA81XfiVAUvaZeAU/Dr5seRzdIPo3wDoiPHUO3A0An7mVZnZtRec5
sPF9fZwcVmjFBgXPSp4T8up5TvLUBcir0HzlaEBBJx6fkOahCd7M1hnvvCxOZ/ST
l6bAyg0HuKP0t94j0K+bg6lXtt7L3Sehsx4r8GgVan2McwpUVKkOGlKMTCWrWWVu
pcPhoyGN4lltQYA6O0Y7o12X6s3RpclfIBRJiqnArPPeEccw20t90um8a+r9dVGT
A/Qojw==
-----END CERTIFICATE-----"""
    CLIENT_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEA0Hl48oikTUeMsHHHfPeF2VEHnpppizWmc1781sfVO0MA6eEu
dgEOfy3mF/nJGjEiMmlhmYjr8LZribpHqKHJSZX3NkYdoWN8UrS7ryZtR5I0q5sD
/wYhPgbAhOkUvMOARM+XJ8+Fv8cJnQUShoFz18QrTpRRdjWV/8e9Sv6JaSZenurV
f8kk7nLvNB3GpnvL76p1GeOy04+WoI4x1mZx8MODsUFnv+wLU8ORDnXLysOkGz6a
tI56bXqLJYfnfUhTX3C0YbiTV5uOGkVQZ9LDJP23uSpqYQ/TXRSJ2MjbdwDBYZxa
bJ0MTBDXaJqUx8g8HKZpmyulAuKsn5r/ewmEbwIDAQABAoIBAFNA72gL4XFrLWgZ
SA1D3BQZI+3WxGdvmXVhbZ9oVmNAMtEzuBYv/dYUQls4yXLIRFvVccCayX5rmy55
UbyqP3Q/i2YFQjf9PtzYiEs+EU4PuTD+yu3BSO04TRHG8x0fBc51CGxBl6wqlFA8
glVsxRJZqOHMoWuPosNuxM16MO3oSB1Hmfzz75jGKyGFQojPVwdRyqB/aulrLo5o
aI87gso+RC56bowJvuL3qA+0Q8THiISenYmZUm1HjVz9JEA33yZPdGaGRVmFptuI
fLQzBRcPIx7XTNtO+W20QmzkTQPJ5liw6FYbs3xnSUZHT1FJ1Mz1IJYxp/UZH+f9
7TfkpmECgYEA8LYTZM3U0IikFUfDEwjzXhd7G+UB53/SyTfSFLz2Q+Aw+gs1Woqw
jnxLX6eSTi85BEVRhpxETE3cFTxUY0X4U28tYNgLXQ9CqpCUC66MQ4XLMj7BNupB
noTBBuTnKFXsvLqU2CCScimtBCbbtbudeSxq/WNuPEWmtJRokpYjoXMCgYEA3bc7
nACACt+W3Pplifcc1bKJtcF65jLF6z8dd/34oYH825wfaKjsqOPs/jFIer2+iBW1
p8Dk2Bl++kSnHvv/IgjtBwcMcgeak8m1adjuS+CTBfytFlQ4Tu9u2/Pa34k93KP8
HQKQFWstCF/T3cAiaEG2V0DBiRG8QKZ4IrukIhUCgYEA1jBuGWi+UcEEoJr2jl2M
kNE8Dpo8k44+NiahnSp3x/YaHqUSmLqIWIFpYHhvy3phtdcosCsk6vDtQUgpnxyH
11Y6fs4/blNB8xwrYCm1TfAj21XT/9V7Bl8Ck+vjdRTgTx+HirmRFlzXQ7aAErob
adOIcGilkqQ3rr/QPX+zvNkCgYEAq7XxEIzCnak0acfzQ7qCNm6jgIRr7kR8TAkB
haDIIi1N67cqDCBnyRVcwjDg9U5mdXZ6zYTytvpoAOOSmsiHe5B2Ie8vkFCbQsIB
IgzD4Tf4JbbfRl/LjDabIPXnGSBtLKhD5SPK+wuaQNYWe7MF8sCRu1mHieSWa2uB
t0SjhVECgYEAuARrac84TmK8RxnYNfVvUwyJsa+NiVLjHGagYS3Nz1OF2ZXUB7wv
qEr8MsnIg3XZiBTvczG+4VJ8By/AeEkeI8GmOO2Xlqc2WbE3nG5Rg+r4kxivGE88
j+hua8zczi52wXtVIUHp1AuPVSTY0fwHFC6aajr7p970vxLVqQEqLhc=
-----END RSA PRIVATE KEY-----"""
    BUFFER_SIZE = 5 * 1024 * 1024

    @mock.patch.dict("os.environ", MeshTestingCommon.os_environ_values)
    def setUp(self):
        """Override setup to use correct application object"""
        super().setUp()
        self.app = MeshFetchMessageChunkApplication()
        self.environment = self.app.system_config["Environment"]

    def setup_mock_aws_environment(self, s3_client, ssm_client):
        """Setup standard environment for tests"""
        location = {"LocationConstraint": "eu-west-2"}
        s3_client.create_bucket(
            Bucket=f"{self.environment}-mesh",
            CreateBucketConfiguration=location,
        )
        file_content = "123456789012345678901234567890123"
        s3_client.put_object(
            Bucket=f"{self.environment}-mesh",
            Key="inbound/testfile.json",
            Body=file_content,
        )
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        # Override with local dev spine mailboxes
        ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/MESH_URL",
            Value=self.MESH_URL,
            Overwrite=True,
        )
        ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/mailboxes/MESH-UI-02/MAILBOX_PASSWORD",
            Value="pwd123456",
            Overwrite=True,
        )
        ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/mailboxes/MESH-UI-02/INBOUND_BUCKET",
            Value=f"{self.environment}-mesh",
            Overwrite=True,
        )
        ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/mailboxes/MESH-UI-02/INBOUND_FOLDER",
            Value="inbound-MESH-UI-02",
            Overwrite=True,
        )
        ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/mailboxes/TEST-PCRM-2/MAILBOX_PASSWORD",
            Value="password",
            Overwrite=True,
        )
        ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/mailboxes/TEST-PCRM-2/INBOUND_BUCKET",
            Value=f"{self.environment}-mesh",
            Overwrite=True,
        )
        ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/mailboxes/TEST-PCRM-2/INBOUND_FOLDER",
            Value="inbound-test-pcrm-2",
            Overwrite=True,
        )
        ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/MESH_CLIENT_CERT",
            Value=self.CLIENT_CERT,
            Overwrite=True,
        )
        ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/MESH_CLIENT_KEY",
            Value=self.CLIENT_KEY,
            Overwrite=True,
        )

    @mock_ssm
    @mock_s3
    def test_handshake(self):
        """Test handshake against real MESH server"""
        s3_client = boto3.client("s3", region_name="eu-west-2")
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        self.setup_mock_aws_environment(s3_client, ssm_client)
        logger = Logger()
        logger.process_name = f"{self.environment}_test_handshake"
        mailbox = MeshMailbox(
            logger, mailbox="MESH-UI-02", environment=f"{self.environment}"
        )
        response = mailbox.handshake()
        self.assertEqual(response, 200)

    @mock_ssm
    @mock_s3
    def test_fetch_chunk(self):
        """Test fetching a chunk"""

        s3_client = boto3.client("s3", region_name="eu-west-2")
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        self.setup_mock_aws_environment(s3_client, ssm_client)
        logger = Logger()
        logger.process_name = f"{self.environment}_test_fetch_chunk"
        mailbox = MeshMailbox(
            logger, mailbox="MESH-UI-02", environment=f"{self.environment}"
        )
        # setup old mailboxes
        old_mailbox1 = OldMeshMailbox(
            logger, mailbox="MESH-UI-02", environment=f"{self.environment}"
        )
        # old_mailbox2 = OldMeshMailbox(
        #     logger, mailbox="TEST-PCRM-2", environment=f"{self.environment}"
        # )

        # Send a test file to the mailbox using old method
        # msg = OldMeshMessage(
        #     "test.dat", b"12345", "TEST-PCRM-2", "MESH-UI-02", "TEST", None
        # )
        # old_mailbox2.send_chunk(msg)

        # poll for message ID using old method
        message_list = old_mailbox1.mesh_client.list_messages()
        self.assertGreaterEqual(len(message_list), 1)
        print(message_list)
        message_id = message_list[0]

        # get message chunk and stream to S3
        response = mailbox.get_chunk(message_id)
        self.assertEqual(response.status_code, 200)
        response.raise_for_status()

        # print(response.headers)
        # print(response.encoding)

        # print(mailbox.params)
        s3_bucket = mailbox.get_param(MeshMailbox.INBOUND_BUCKET)
        s3_folder = mailbox.get_param(MeshMailbox.INBOUND_FOLDER)
        s3_key = s3_folder + "/" if len(s3_folder) > 0 else ""
        file_name = response.headers["Mex-Filename"]
        s3_key += file_name if len(file_name) > 0 else message_id + ".dat"
        # print(s3_bucket)
        # print(s3_key)

        multipart_upload = s3_client.create_multipart_upload(
            Bucket=s3_bucket, Key=s3_key
        )

        upload_id = multipart_upload["UploadId"]
        part_number = 1
        etags = []

        # decompressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
        for buffer in response.iter_content(chunk_size=self.BUFFER_SIZE):
            # print(buffer)

            # if encoding is gzip:
            #     # Note potential 10:1/20:1 size increase here. 5MB -> 50MB/100MB
            #     # Ensure lambda memory limit is set appropriately
            #     sendbuffer = decompressor.uncompress(buffer)
            # else:
            #     sendbuffer = buffer]
            response = s3_client.upload_part(
                Body=buffer,
                Bucket=s3_bucket,
                Key=s3_key,
                PartNumber=part_number,
                ContentLength=len(buffer),
                UploadId=upload_id,
            )
            # print(response["ETag"])
            etags.append(
                {
                    "ETag": response["ETag"],
                    "PartNumber": part_number,
                }
            )
            part_number += 1

        response = s3_client.complete_multipart_upload(
            Bucket=s3_bucket,
            Key=s3_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": etags},
        )

        # Check S3 uploaded message
        response = s3_client.head_object(
            Bucket=s3_bucket, Key=s3_key, ChecksumMode="ENABLED"
        )
        # print(response)


    @mock_ssm
    @mock_s3
    def test_poll_messages(self):
        """Test sending a chunk"""
        s3_client = boto3.client("s3", region_name="eu-west-2")
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        self.setup_mock_aws_environment(s3_client, ssm_client)
        logger = Logger()
        mailbox = MeshMailbox(
            logger, mailbox="MESH-UI-02", environment=f"{self.environment}"
        )
        response, message_list = mailbox.list_messages()
        old_mailbox1 = OldMeshMailbox(
            logger, mailbox="MESH-UI-02", environment=f"{self.environment}"
        )
        old_message_list = old_mailbox1.mesh_client.list_messages()
        self.assertEqual(old_message_list, message_list)

    @mock_ssm
    @mock_s3
    def test_acknowledge_message(self):
        """Test sending a chunk"""
        s3_client = boto3.client("s3", region_name="eu-west-2")
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        self.setup_mock_aws_environment(s3_client, ssm_client)
        logger = Logger()
        mailbox = MeshMailbox(
            logger, mailbox="MESH-UI-02", environment=f"{self.environment}"
        )
        old_mailbox2 = OldMeshMailbox(
            logger, mailbox="TEST-PCRM-2", environment=f"{self.environment}"
        )

        # Send a test file to the mailbox using old method
        msg1 = OldMeshMessage(
            "test.dat", b"12345", "TEST-PCRM-2", "MESH-UI-02", "TEST", None
        )
        old_mailbox2.send_chunk(msg1)
        msg2 = OldMeshMessage(
            "test.dat", b"67891", "TEST-PCRM-2", "MESH-UI-02", "TEST", None
        )
        old_mailbox2.send_chunk(msg2)

        response_pre_acknowledge, message_list_pre_acknowledge = mailbox.list_messages()
        first_message_id = message_list_pre_acknowledge[0]

        self.assertIn(first_message_id, message_list_pre_acknowledge)

        mailbox.acknowledge_message(first_message_id)
        response_post_acknowledge, message_list_post_acknowledge = mailbox.list_messages()
        self.assertNotIn(first_message_id, message_list_post_acknowledge)

        # old_mailbox1 = OldMeshMailbox(
        #     logger, mailbox="MESH-UI-02", environment=f"{self.environment}"
        # )
        # old_message_list = old_mailbox1.mesh_client.list_messages()


## compression example
# with requests.get(url, stream=True, verify=False) as r:
#     if save_file_path.endswith('gz'):
#         compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
#         with open(save_file_path, 'wb') as f:
#             for chunk in r.iter_content(chunk_size=1024*1024):
#                 f.write(compressor.compress(chunk))
#             f.write(compressor.flush())
#     else:
#         with open(save_file_path, 'wb') as f:
#             shutil.copyfileobj(r.raw, f)
