# spine-core-aws-common

Common code used across Spine projects in AWS

## Installation

Simply add the pre-built package to your python environment.

### PIP

```
pip install https://github.com/NHSDigital/spine-core-aws-common/releases/download/v0.1.1/spine_aws_common-0.1.1-py3-none-any.whl
```

### requirements.txt

```
https://github.com/NHSDigital/spine-core-aws-common/releases/download/v0.1.1/spine_aws_common-0.1.1-py3-none-any.whl
```

### Poetry

```
poetry add https://github.com/NHSDigital/spine-core-aws-common/releases/download/v0.1.1/spine_aws_common-0.1.1-py3-none-any.whl
```

## Usage

TBC

Quick example

```python
from spine_aws_common import LambdaApplication

class MyApp(LambdaApplication):
    def initialise(self):
        # initialise
        return

    def start(self):
        # do actual work
        # to set response for the lambda
        self.response = '{"my new response":true}'
        return

# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MyApp(additional_log_config='/path/to/mylogconfig.cfg')

def lambda_handler(event, context):
    return app.main(event, context)
```

API Gateway example

```python
from spine_aws_common import APIGatewayApplication
from aws_lambda_powertools.event_handler.api_gateway import Response

class MyApp(APIGatewayApplication):
    def get_hello(self):
        return Response(
            status_code=200, content_type="application/json", body='{"hello":"world"}'
        )

    def get_id(self, _id):
        response_dict = {"id": _id}
        return Response(
            status_code=200,
            content_type="application/json",
            body=json.dumps(response_dict),
        )

    def configure_routes(self):
        self._add_route(self.get_hello, "/hello")
        self._add_route(self.get_id, "/id/<_id>")

# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MyApp(additional_log_config='/path/to/mylogconfig.cfg')

def lambda_handler(event, context):
    return app.main(event, context)
```
