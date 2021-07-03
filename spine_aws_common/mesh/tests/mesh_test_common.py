"""Common methods and classes used for testing mesh client"""


class MeshTestCommon:
    """Mock helpers"""

    @classmethod
    def do_nothing(cls):
        """What it says on the tin"""

    CONTEXT = {"aws_request_id": "TESTREQUEST"}
    KNOWN_INTERNAL_ID = "20210701225219765177_TESTER"

    def get_known_internal_id(self):  # pylint: disable=no-self-use
        """Get a known internal Id for testing and mocking purposes"""
        return "20210701225219765177_TESTER"

    @staticmethod
    def setup_step_function(sfn_client, environment, step_function_name):
        """Setup a mock step function with name from environment"""
        if not environment:
            environment = "default"
        step_func_definition = {
            "Comment": "Test step function",
            "StartAt": "HelloWorld",
            "States": {
                "HelloWorld": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:eu-west-2:123456789012:function:HW",
                    "End": True,
                }
            },
        }
        return sfn_client.create_state_machine(
            definition=f"{step_func_definition}",
            loggingConfiguration={
                "destinations": [{"cloudWatchLogsLogGroup": {"logGroupArn": "xxx"}}],
                "includeExecutionData": False,
                "level": "ALL",
            },
            name=step_function_name,
            roleArn="arn:aws:iam::123456789012:role/StepFunctionRole",
            tags=[{"key": "environment", "value": environment}],
            tracingConfiguration={"enabled": False},
            type="STANDARD",
        )
