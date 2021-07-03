""" Testing MeshPollMailbox application """
import json
from unittest import mock, TestCase
from spine_aws_common.mesh import MeshPollMailboxApplication


class TestMeshPollMailboxApplication(TestCase):
    """ Testing MeshPollMailbox application """

    def setUp(self):
        pass

    @mock.patch.dict(
        "os.environ",
        values={
            "AWS_REGION": "eu-west-2",
            "AWS_EXECUTION_ENV": "AWS_Lambda_python3.8",
            "AWS_LAMBDA_FUNCTION_NAME": "lambda_test",
            "AWS_LAMBDA_FUNCTION_MEMORY_SIZE": "128",
            "AWS_LAMBDA_FUNCTION_VERSION": "1",
        },
    )
    def test_mesh_poll_mailbox(self):
        """ Test the lambda """
        mailbox = "A01AA123"
        event = {
            "mailbox": mailbox
        }
        context = {
            "aws_request_id": "TESTRUN"
        }
        response = MeshPollMailboxApplication(
            "mesh_application.cfg").main(event=event, context=context)
        print(json.dumps(event))
        print(json.dumps(response))
        self.assertEqual(1, response["body"]["messageCount"])
        self.assertLogs("LAMBDA0001", level="INFO")
        self.assertLogs("LAMBDA0002", level="INFO")
        self.assertLogs("LAMBDA0003", level="INFO")

    # def test_lambda_additional_logging(self):
    #     app = MeshPollMailboxApplication(
    #         additional_log_config=f"{__file__}/add_config.cfg")
    #     app.log_object.write_log(
    #         "ADDTEST001",
    #         None,
    #         None,
    #     )
    #     self.assertLogs("ADDTEST001", level="INFO")
