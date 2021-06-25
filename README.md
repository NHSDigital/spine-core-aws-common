# spine-core-aws-common

Common code used across Spine projects in AWS

## Installation

Simply add the pre-built package to your python environment.

### PIP

```
pip install https://github.com/NHSDigital/spine-core-aws-common/releases/download/v0.0.1/spine_aws_common-0.0.1-py3-none-any.whl
```

### requirements.txt

```
https://github.com/NHSDigital/spine-core-aws-common/releases/download/v0.0.1/spine_aws_common-0.0.1-py3-none-any.whl
```

### Poetry

```
poetry add https://github.com/NHSDigital/spine-core-aws-common/releases/download/v0.0.1/spine_aws_common-0.0.1-py3-none-any.whl
```

## Usage

TBC

Quick example

```
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
app = MyApp()

def lambda_handler(event, context):
    return app.main(event, context)
```
