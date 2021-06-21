"""
AWS Lambda function for checking MESH mailbox via API
"""
from abc import abstractmethod
import json
import boto3
import tempfile
from botocore.client import Config
from botocore.exceptions import ClientError
from spinecore.lambda_application import LambdaApplication
from mesh_client import MeshClient


class MeshApiApplication(LambdaApplication):
    """
    Class to poll and receive messages or send messages via the MESH API
    """

    def _getSSMParameter(self, parameterPath, encrypted=True, required=True):
        """
        Helper function to get SSM parameters
        """
        try:
            environment = self.systemConfig['ENV']
            ParameterName = f'/{environment}{parameterPath}'
            self.logObject.writeLog('MESHAPI001a', None, {
                                    'parameter': ParameterName})
            value = self.ssmClient.get_parameter(
                Name=ParameterName,
                WithDecryption=encrypted)['Parameter']['Value']
        except ClientError as e:
            # TODO Log error
            if required:
                raise e
            value = None
        return value

    def _getMeshConfigFromParamStore(self, mailbox):
        """
        Get config from SSM Parameter Store. Need to extract and pass the 
        mailbox name based on your application
        """
        self.ssmClient = boto3.client('ssm')
        self.logObject.writeLog('MESHAPI001', None, None)

        self.systemConfig['BATCH_SIZE'] = self._getSSMParameter(
            '/mesh/BATCH_SIZE', encrypted=False, required=False)
        if not self.systemConfig['BATCH_SIZE']:
            # default batch size
            self.systemConfig['BATCH_SIZE'] = 10

        self.systemConfig['MESH_URL'] = self._getSSMParameter(
            '/mesh/MESH_URL', encrypted=False)
        self.systemConfig['MESH_SHARED_KEY'] = self._getSSMParameter(
            '/mesh/MESH_SHARED_KEY')
        self.systemConfig['MESH_SQS_QUEUE_URL'] = self._getSSMParameter(
            f'/mesh/mailboxes/{mailbox}/MESH_SQS_QUEUE_URL',
            encrypted=False)
        self.systemConfig['MAILBOX_NAME'] = mailbox
        self.systemConfig['MAILBOX_PASSWORD'] = self._getSSMParameter(
            f'/mesh/mailboxes/{mailbox}/MAILBOX_PASSWORD')
        self.systemConfig['MESH_VERIFY_SSL'] = self._getSSMParameter(
            '/mesh/MESH_VERIFY_SSL', encrypted=False)
        self.systemConfig['CA_CERT'] = self._getSSMParameter(
            '/mesh/MESH_CA_CERT',
            required=self.systemConfig['MESH_VERIFY_SSL'])
        self.systemConfig['MESH_CERT'] = self._getSSMParameter(
            '/mesh/MESH_CLIENT_CERT')
        self.systemConfig['MESH_KEY'] = self._getSSMParameter(
            '/mesh/MESH_CLIENT_KEY')

        self.logObject.writeLog('MESHAPI008', None,
                                {'mailbox': mailbox,
                                 'meshSqsQueue': self.systemConfig['MESH_SQS_QUEUE_URL']})

    def _getMeshClient(self, mailbox, password, tempDirName):
        meshSharedKey = self.systemConfig['MESH_SHARED_KEY'].encode('utf-8')
        self.logObject.writeLog('MESHAPI004', None, None)
        meshClientCertFileName, meshClientKeyFileName, meshCaCertFilename = \
            self._saveMeshCertificates(tempDirName)
        self.logObject.writeLog('MESHAPI005', None,
                                {'meshUrl': self.systemConfig['MESH_URL']})
        mesh_client = MeshClient(
            url=self.systemConfig['MESH_URL'],
            mailbox=mailbox,
            password=password,
            shared_key=meshSharedKey,
            cert=(meshClientCertFileName, meshClientKeyFileName),
            verify=meshCaCertFilename
        )
        self.logObject.writeLog('MESHAPI006', None, None)
        mesh_client.handshake()
        self.logObject.writeLog('MESHAPI007', None, None)
        return mesh_client

    def _saveMeshCertificates(self, tempDir):
        """
        Save mesh certs to tempDir
        """
        meshClientCert = self.systemConfig['MESH_CERT']
        meshClientKey = self.systemConfig['MESH_KEY']
        meshCaCert = self.systemConfig['CA_CERT']

        # store as temporary files for the mesh client
        meshClientCertFile = tempfile.NamedTemporaryFile(
            dir=tempDir, delete=False)
        meshClientCertFile.write(meshClientCert.encode('utf-8'))
        meshClientKeyFile = tempfile.NamedTemporaryFile(
            dir=tempDir, delete=False)
        meshClientKeyFile.write(meshClientKey.encode('utf-8'))

        meshCaCertFilename = None
        if self.systemConfig['MESH_VERIFY_SSL'] == "True":
            meshCaCertFile = tempfile.NamedTemporaryFile(
                dir=tempDir, delete=False)
            meshCaCertFile.write(meshCaCert.encode('utf-8'))
            meshCaCertFilename = meshCaCertFile.name

        return meshClientCertFile.name, meshClientKeyFile.name, meshCaCertFilename


class MeshPollApplication(MeshApiApplication):

    def start(self):
        """
        Start getting messages from MESH mailbox
        """
        # TODO think about eventbridge

        # Get mailbox name from event and get config from SSM parameter store
        mailbox = self.event.get('mailbox')
        if mailbox == "[ENV]":
            mailbox = self.systemConfig['ENV']
        self.logObject.writeLog('MESHPOLL001', None, {'mailbox': mailbox})
        self._getMeshConfigFromParamStore(mailbox)
        messageList = self._getPendingMessagesList(
            mailbox,
            self.systemConfig['MAILBOX_PASSWORD'])
        if messageList:
            self._postMeshMessagesToSqs(messageList)
        return {'statusCode': 200}

    def _getPendingMessagesList(self, mailbox, password):
        """
        Get list of messages waiting in MESH mailbox 
        """
        with tempfile.TemporaryDirectory() as tempDirName:
            self.logObject.writeLog('MESHPOLL002', None, None)
            meshClient = self._getMeshClient(mailbox, password, tempDirName)

            self.logObject.writeLog('MESHPOLL003', None, None)
            meshClient.handshake()

            messageList = meshClient.list_messages()
            if messageList:
                self.logObject.writeLog('MESHPOLL005', None, {
                                        'messageCount': len(messageList)})
            else:
                self.logObject.writeLog('MESHPOLL005', None, {
                                        'messageCount': 0})

            meshClient.close()
            self.logObject.writeLog('MESHPOLL006', None, None)

        return messageList

    def _batchList(self, messageList, batchSize):
        '''
        Batch helper
        '''
        return (messageList[i: i + batchSize] for i in range(0, len(messageList), batchSize))

    # TODO Eventbridge?
    def _postMeshMessagesToSqs(self, messageList):
        """
        Post MESH messages to be retreived to SQS queue in batches
        """
        sqsClient = boto3.client(
            'sqs', config=Config(retries={'max_attempts': 3}))
        messageBatches = self._batchList(
            messageList, self.systemConfig['BATCH_SIZE'])

        for batch in messageBatches:
            entries = []
            for messageId in batch:
                self.logObject.writeLog('MESHPOLL007', None, {'messageId': messageId})
                internalID = self._createNewInternalID()  # New internalID for each message
                messageToSend = {
                    'internalID': internalID,
                    'mailbox': self.systemConfig['MAILBOX_NAME'],
                    'messageId': messageId
                }
                formattedMessageToSend = {
                    'Id': messageId,
                    'MessageBody': json.dumps(messageToSend)
                }
                entries.append(formattedMessageToSend)

            response = sqsClient.send_message_batch(
                QueueUrl=self.systemConfig['MESH_SQS_QUEUE_URL'],
                Entries=entries
            )

            if response.get('Failed', []):
                self.logObject.writeLog('MESHPOLL008', None, {"response": response})
                raise Exception('Unable to send batch to SQS')


class MeshFetchMessageApplication(MeshApiApplication):

    def start(self):
        """
        """
        sqsMessage = self.event
        mailbox = sqsMessage['mailbox']
        messageId = sqsMessage['messageId']
        self.internalID = sqsMessage['internalID']
        self.logObject.setInternalID(self.internalID)
        self.logObject.writeLog('MESHFETCH001', None, {'mailbox': mailbox, 'messageId': messageId})
        self._getMeshConfigFromParamStore(mailbox)
        self._fetch_message(messageId)

    def _fetch_message(self, messageId):
        """
        log({'log_reference': LogReference.FETCHMESH0001})

        cloudwatch_event_rule = sqs_message['cloudwatch_event_rule']
        message_id = sqs_message['message_id']

        log({'log_reference': LogReference.FETCHMESH0003, 'cloudwatch_event_rule': cloudwatch_event_rule})
        mesh_mailbox_creds = json.loads(get_secret_by_key('mesh_mailbox_credentials',
                                        extract_mailbox_secret_key(cloudwatch_event_rule)))

        mailbox_id = mesh_mailbox_creds['mailbox_id']
        if mailbox_id == "[ENV]":
            mailbox_id = ENVIRONMENT_NAME

        with tempfile.TemporaryDirectory() as temp_dir_name:
            with get_mesh_client(mailbox_id, mesh_mailbox_creds['password'], temp_dir_name) as mesh_client:
                file_name, from_mailbox_id,  file_contents = get_message_contents_by_message_id(message_id, mesh_client)
                log({'log_reference': LogReference.FETCHMESH0004, 'mailbox_id': mailbox_id,
                    'from_mailbox_id': from_mailbox_id, 'message_id': message_id, 'message_length': len(file_contents)})

                if not is_valid_from_mailbox(cloudwatch_event_rule, from_mailbox_id):
                    log({'log_reference': LogReference.FETCHMESH0009})
                    mesh_client.close()
                    raise InvalidMailboxIdException(from_mailbox_id)

                target_bucket = get_s3_bucket_name_from_cloudwatch_event_rule(cloudwatch_event_rule)
                upload_file_to_s3(target_bucket, file_contents, file_name)

                log({'log_reference': LogReference.FETCHMESH0007})
                mesh_client.acknowledge_message(message_id)
                log({'log_reference': LogReference.FETCHMESH0008})
                mesh_client.close()
        """
        pass


class MetadataNotFoundException(Exception):
    """
    Mesh credentials error
    """

    def __init__(self, msg='Object missing srcmailbox, destmailbox or workflowid metadata'):
        super(MetadataNotFoundException, self).__init__()
        self.msg = msg


class MeshSendMessageApplication(MeshApiApplication):

    def start(self):
        """
        """
        self.logObject.writeLog('MESHSEND001', None, None)
        self.s3Client = boto3.client('s3')

        record = self.event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        # TODO read mapping from SSM parameter store, then try metadata
        response = self.s3Client.head_object(Bucket=bucket, Key=key)
        metadata = response['ResponseMetadata']['HTTPHeaders']
        self.logObject.writeLog('MESHSEND001a', None,
                                {'bucket': bucket, 'filename': key, 'metadata': metadata})
        try:
            srcMailbox = metadata['x-amz-meta-srcmailbox']
            destMailbox = metadata['x-amz-meta-destmailbox']
            workflowId = metadata['x-amz-meta-workflowid']
        except KeyError as e:
            raise MetadataNotFoundException(e)

        if srcMailbox == "[ENV]":
            srcMailbox = self.systemConfig['ENV']
        if destMailbox == "[ENV]":
            destMailbox = self.systemConfig['ENV']
        self.logObject.writeLog('MESHSEND002', None,
                                {'srcMailbox': srcMailbox,
                                 'destMailbox': destMailbox,
                                 'workflowId': workflowId})

        self._getMeshConfigFromParamStore(srcMailbox)
        srcMailboxPassword = self.systemConfig['MAILBOX_PASSWORD']
        status = self._sendMessage(
            bucket, key, srcMailbox, srcMailboxPassword, destMailbox, workflowId)
        return {'statusCode': status}

    def _sendMessage(self, bucket, key, srcMailbox, srcMailboxPassword, destMailbox, workflowId):
        """
        Send a mesh message
        """
        encodedFileContents = self._getFileContents(bucket, key)
        with tempfile.TemporaryDirectory() as tempDirName:
            self.logObject.writeLog('MESHSEND004', None, None)
            meshClient = self._getMeshClient(
                srcMailbox, srcMailboxPassword, tempDirName)
            self.logObject.writeLog('MESHSEND005', None, None)
            messageId = meshClient.send_message(
                destMailbox, encodedFileContents, workflow_id=workflowId)
            self.logObject.writeLog('MESHSEND006', None, {
                                    'messageId': messageId})
        meshClient.close()

        # TODO
        # log({'log_reference': LogReference.SENDMESHMESSAGE0009, 'target_bucket': COMPLETED_BUCKET})
        # put_object(COMPLETED_BUCKET, file_contents, key)
        # log({'log_reference': LogReference.SENDMESHMESSAGE0010})

        # log({'log_reference': LogReference.SENDMESHMESSAGE0012, 'target_bucket': full_bucket_name})
        # delete_object_from_bucket(bucket, key)
        # log({'log_reference': LogReference.SENDMESHMESSAGE0013})

        return 200

    def _getFileContents(self, bucket, key):
        self.logObject.writeLog('MESHSEND003', None, {
                                'bucket': bucket, 'key': key})
        fileObject = self.s3Client.get_object(Bucket=bucket, Key=key)
        fileContents = fileObject.get('Body').read().decode('utf-8')
        return fileContents.encode('utf-8')


'''
def get_message_contents_by_message_id(message_id, mesh_client):
    log({'log_reference': LogReference.MESHCLIENT0023})
    message = mesh_client.retrieve_message(message_id)
    log({'log_reference': LogReference.MESHCLIENT0024})
    file_name = message.mex_header('filename')
    from_mailbox_id = message.mex_header('from')
    file_contents = message.read()
    log({'log_reference': LogReference.MESHCLIENT0025, 'file_name': file_name, 'from_mailbox_id': from_mailbox_id})
    message.close()
    return file_name, from_mailbox_id,  file_contents

'''
