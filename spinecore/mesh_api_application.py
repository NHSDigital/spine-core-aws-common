"""
AWS Lambda function for checking MESH mailbox via API
"""
from abc import abstractmethod
import json
import ntpath
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
        # TODO standardise events
        # TODO think about better way of doing the environment name (read tag?)
        # Get mailbox name from event and get config from SSM parameter store
        mailbox = self.event.get('mailbox')
        if mailbox == "[ENV]":
            mailbox = self.systemConfig['ENV']
        self.logObject.writeLog('MESHPOLL001', None, {'mailbox': mailbox})
        self._getMeshConfigFromParamStore(mailbox)
        # TODO check SQS queue to see if there are messages waiting to fetch
        # before polling MESH to prevent duplication of messages in queue
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

        # TODO standardise events
        for batch in messageBatches:
            entries = []
            for messageId in batch:
                self.logObject.writeLog('MESHPOLL007', None, {
                                        'messageId': messageId})
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
                self.logObject.writeLog('MESHPOLL008', None, {
                                        "response": response})
                raise Exception('Unable to send batch to SQS')


class MeshFetchMessageApplication(MeshApiApplication):

    def start(self):
        """
        """
        sqsMessage = self.event
        mailbox = sqsMessage['mailbox']
        if mailbox == "[ENV]":
            mailbox = self.systemConfig['ENV']
        messageId = sqsMessage['messageId']
        self.internalID = sqsMessage['internalID']
        self.logObject.setInternalID(self.internalID)
        self.logObject.writeLog(
            'MESHFETCH001', None, {'mailbox': mailbox, 'messageId': messageId})
        self._getMeshConfigFromParamStore(mailbox)
        self._fetchMessage(mailbox, messageId)
        return {'statusCode': 200}

    def _fetchMessage(self, mailbox, messageId):
        """
        Get message from MESH mailbox
        """
        with tempfile.TemporaryDirectory() as tempDirName:
            meshClient = self._getMeshClient(
                mailbox,
                self.systemConfig['MAILBOX_PASSWORD'],
                tempDirName)

            fileName, srcMailbox, fileContents = self._getMessageContents(
                meshClient, messageId)

            # self.logObject.writeLog(
            #    'MESHFETCH009', None, {'mailbox': mailbox, 'messageId': messageId})

            """
            TODO mailbox validation, to add
            if not is_valid_from_mailbox(cloudwatch_event_rule, from_mailbox_id):
                log({'log_reference': LogReference.FETCHMESH0009})
                mesh_client.close()
                raise InvalidMailboxIdException(from_mailbox_id)
            """
            # TODO find correct bucket name and folder from config
            # log({'log_reference': LogReference.FETCHMESH0007})
            targetBucket="meshtest-supplementary-data"
            folder="inbound/"
            self._saveFileToS3(targetBucket, fileContents, folder, fileName)

            # log({'log_reference': LogReference.FETCHMESH0008})
            meshClient.acknowledge_message(messageId)
            meshClient.close()

    def _getMessageContents(self, meshClient, messageId):
        """
        Get message contents from MESH
        """
        # TODO Safe chunking - see bottom of file
        # log({'log_reference': LogReference.MESHCLIENT0023})
        self.logObject.writeLog(
            'MESHFETCH002', None, None)
        message = meshClient.retrieve_message(messageId)
        # log({'log_reference': LogReference.MESHCLIENT0024})
        fileName = message.mex_header('filename')
        srcMailbox = message.mex_header('from')
        localId = message.mex_header('localID')
        if not localId:
            localId = "NotProvided"
        fileContents = message.read()

        self.logObject.writeLog(
            'MESHFETCH003', None,
            {'fileName': fileName,
             'srcMailbox': srcMailbox,
             'localId': localId,
             'messageSize': len(fileContents)})
        message.close()
        return fileName, srcMailbox, fileContents

    def _saveFileToS3(self, targetBucket, fileContents, folder, fileName):
        # log({'log_reference': LogReference.FETCHMESH0005, 'target_bucket': target_bucket, 'file_name': file_name})
        s3Client = boto3.client('s3')
        meta_data = {
            'internal_id': self.internalID
        }
        targetKey = f'{folder}{fileName}'
        self.logObject.writeLog(
            'MESHFETCH004', None, {'bucket': targetBucket, 'key': targetKey})
        s3Client.put_object(Bucket=targetBucket, Key=targetKey,
                            Metadata=meta_data, Body=fileContents)
        # log({'log_reference': LogReference.FETCHMESH0006})

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
            fileName = ntpath.basename(key)
            self.logObject.writeLog('MESHSEND004', None, None)
            meshClient = self._getMeshClient(
                srcMailbox, srcMailboxPassword, tempDirName)
            self.logObject.writeLog('MESHSEND005', None, {
                                    'filename': fileName})
            messageId = meshClient.send_message(
                destMailbox, encodedFileContents, workflow_id=workflowId,
                filename=fileName, local_id=self.internalID)
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

# TODO to get around issues with lambda 15 mins max timeouts, each chunk is
# downloaded by a separate lambda, chunks put on the Eventbridge
# look at Step Functions and/or EventBridge

class MeshFetchMessageChunkApplication(MeshApiApplication):
    # use Multipart upload
    pass

class MeshSendMessageChunkApplication(MeshApiApplication):
    # use range and partNumber
    pass
