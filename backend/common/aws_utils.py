"""
AWS integration utilities for Careficient pipelines.
Supports S3, Lambda, Step Functions, and other AWS services.
"""

import logging
from typing import Optional, Dict, Any, List, BinaryIO
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# AWS service stubs - ready for actual implementation


class S3Manager:
    """
    Manage S3 bucket operations.
    
    Example:
        s3 = S3Manager(bucket_name="careficient-docs")
        s3.upload_file("document.pdf", "documents/doc1.pdf")
        url = s3.get_signed_url("documents/doc1.pdf")
    """
    
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        """
        Initialize S3 manager.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
        """
        try:
            import boto3
            self.s3_client = boto3.client('s3', region_name=region)
            self.bucket_name = bucket_name
            self.region = region
            logger.info(f"S3Manager initialized for bucket: {bucket_name}")
        except ImportError:
            logger.warning("boto3 not installed - S3 operations will fail")
            self.s3_client = None
    
    def upload_file(
        self,
        file_path: str,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Upload file to S3.
        
        Args:
            file_path: Local file path
            s3_key: S3 object key
            metadata: Optional metadata
        
        Returns:
            S3 URL or None if failed
        """
        if not self.s3_client:
            logger.error("S3 client not available")
            return None
        
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key, ExtraArgs=extra_args)
            url = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Uploaded {file_path} to {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload {file_path} to S3: {e}")
            return None
    
    def upload_bytes(
        self,
        data: bytes,
        s3_key: str,
        content_type: str = "application/octet-stream"
    ) -> Optional[str]:
        """
        Upload bytes to S3.
        
        Args:
            data: Bytes to upload
            s3_key: S3 object key
            content_type: MIME type
        
        Returns:
            S3 URL or None if failed
        """
        if not self.s3_client:
            logger.error("S3 client not available")
            return None
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=data,
                ContentType=content_type
            )
            url = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Uploaded {len(data)} bytes to {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload bytes to S3: {e}")
            return None
    
    def download_file(self, s3_key: str, file_path: str) -> bool:
        """
        Download file from S3.
        
        Args:
            s3_key: S3 object key
            file_path: Local file path
        
        Returns:
            True if successful
        """
        if not self.s3_client:
            logger.error("S3 client not available")
            return False
        
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, file_path)
            logger.info(f"Downloaded {s3_key} to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {s3_key} from S3: {e}")
            return False
    
    def download_bytes(self, s3_key: str) -> Optional[bytes]:
        """
        Download file from S3 as bytes.
        
        Args:
            s3_key: S3 object key
        
        Returns:
            File bytes or None if failed
        """
        if not self.s3_client:
            logger.error("S3 client not available")
            return None
        
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            data = response['Body'].read()
            logger.info(f"Downloaded {len(data)} bytes from {s3_key}")
            return data
        except Exception as e:
            logger.error(f"Failed to download {s3_key} from S3: {e}")
            return None
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3.
        
        Args:
            s3_key: S3 object key
        
        Returns:
            True if successful
        """
        if not self.s3_client:
            logger.error("S3 client not available")
            return False
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted {s3_key} from S3")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {s3_key} from S3: {e}")
            return False
    
    def get_signed_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Get signed URL for S3 object.
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration in seconds
        
        Returns:
            Signed URL or None if failed
        """
        if not self.s3_client:
            logger.error("S3 client not available")
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            logger.debug(f"Generated signed URL for {s3_key}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL for {s3_key}: {e}")
            return None
    
    def list_files(self, prefix: str = "", max_keys: int = 1000) -> List[str]:
        """
        List files in S3 bucket.
        
        Args:
            prefix: Object key prefix
            max_keys: Maximum number of keys to return
        
        Returns:
            List of object keys
        """
        if not self.s3_client:
            logger.error("S3 client not available")
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            keys = [obj['Key'] for obj in response.get('Contents', [])]
            logger.debug(f"Listed {len(keys)} files with prefix {prefix}")
            return keys
        except Exception as e:
            logger.error(f"Failed to list files in S3: {e}")
            return []


class LambdaManager:
    """
    Manage Lambda function invocations.
    
    Example:
        lambda_mgr = LambdaManager()
        result = lambda_mgr.invoke("process-document", {"document_id": "doc123"})
    """
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize Lambda manager.
        
        Args:
            region: AWS region
        """
        try:
            import boto3
            self.lambda_client = boto3.client('lambda', region_name=region)
            self.region = region
            logger.info("LambdaManager initialized")
        except ImportError:
            logger.warning("boto3 not installed - Lambda operations will fail")
            self.lambda_client = None
    
    def invoke(
        self,
        function_name: str,
        payload: Dict[str, Any],
        async_invoke: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Invoke Lambda function.
        
        Args:
            function_name: Lambda function name
            payload: Function payload
            async_invoke: Whether to invoke asynchronously
        
        Returns:
            Response or None if failed
        """
        if not self.lambda_client:
            logger.error("Lambda client not available")
            return None
        
        try:
            import json
            invocation_type = "Event" if async_invoke else "RequestResponse"
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType=invocation_type,
                Payload=json.dumps(payload)
            )
            
            logger.info(f"Invoked Lambda function: {function_name}")
            return response
        except Exception as e:
            logger.error(f"Failed to invoke Lambda function {function_name}: {e}")
            return None


class StepFunctionsManager:
    """
    Manage AWS Step Functions state machine executions.
    
    Example:
        sfn = StepFunctionsManager()
        execution = sfn.start_execution(
            "document-processing-workflow",
            {"document_id": "doc123"}
        )
    """
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize Step Functions manager.
        
        Args:
            region: AWS region
        """
        try:
            import boto3
            self.sfn_client = boto3.client('stepfunctions', region_name=region)
            self.region = region
            logger.info("StepFunctionsManager initialized")
        except ImportError:
            logger.warning("boto3 not installed - Step Functions operations will fail")
            self.sfn_client = None
    
    def start_execution(
        self,
        state_machine_arn: str,
        input_data: Dict[str, Any],
        execution_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Start state machine execution.
        
        Args:
            state_machine_arn: State machine ARN
            input_data: Execution input
            execution_name: Optional execution name
        
        Returns:
            Execution ARN or None if failed
        """
        if not self.sfn_client:
            logger.error("Step Functions client not available")
            return None
        
        try:
            import json
            from datetime import datetime
            
            if not execution_name:
                execution_name = f"exec-{datetime.now().timestamp()}"
            
            response = self.sfn_client.start_execution(
                stateMachineArn=state_machine_arn,
                name=execution_name,
                input=json.dumps(input_data)
            )
            
            logger.info(f"Started execution: {response['executionArn']}")
            return response['executionArn']
        except Exception as e:
            logger.error(f"Failed to start execution: {e}")
            return None


class DynamoDBManager:
    """
    Manage DynamoDB table operations.
    
    Example:
        dynamo = DynamoDBManager("documents-table")
        dynamo.put_item({"id": "doc123", "filename": "scan.pdf"})
        item = dynamo.get_item("doc123")
    """
    
    def __init__(self, table_name: str, region: str = "us-east-1"):
        """
        Initialize DynamoDB manager.
        
        Args:
            table_name: DynamoDB table name
            region: AWS region
        """
        try:
            import boto3
            dynamodb = boto3.resource('dynamodb', region_name=region)
            self.table = dynamodb.Table(table_name)
            self.table_name = table_name
            logger.info(f"DynamoDBManager initialized for table: {table_name}")
        except ImportError:
            logger.warning("boto3 not installed - DynamoDB operations will fail")
            self.table = None
    
    def put_item(self, item: Dict[str, Any]) -> bool:
        """
        Put item in DynamoDB table.
        
        Args:
            item: Item to put
        
        Returns:
            True if successful
        """
        if not self.table:
            logger.error("DynamoDB table not available")
            return False
        
        try:
            self.table.put_item(Item=item)
            logger.debug(f"Put item in {self.table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to put item in DynamoDB: {e}")
            return False
    
    def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get item from DynamoDB table.
        
        Args:
            key: Item key
        
        Returns:
            Item or None if not found
        """
        if not self.table:
            logger.error("DynamoDB table not available")
            return None
        
        try:
            response = self.table.get_item(Key=key)
            item = response.get('Item')
            logger.debug(f"Retrieved item from {self.table_name}")
            return item
        except Exception as e:
            logger.error(f"Failed to get item from DynamoDB: {e}")
            return None
    
    def delete_item(self, key: Dict[str, Any]) -> bool:
        """
        Delete item from DynamoDB table.
        
        Args:
            key: Item key
        
        Returns:
            True if successful
        """
        if not self.table:
            logger.error("DynamoDB table not available")
            return False
        
        try:
            self.table.delete_item(Key=key)
            logger.debug(f"Deleted item from {self.table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete item from DynamoDB: {e}")
            return False


class AWSConfig:
    """AWS configuration and utilities."""
    
    # Standard S3 bucket names for Careficient
    BUCKETS = {
        "documents": "careficient-documents",
        "audio": "careficient-audio",
        "processed": "careficient-processed",
        "logs": "careficient-logs",
    }
    
    # Standard DynamoDB table names
    TABLES = {
        "documents": "careficient-documents",
        "extractions": "careficient-extractions",
        "oasis-prefills": "careficient-oasis-prefills",
    }
    
    # Standard Lambda functions
    FUNCTIONS = {
        "transcribe": "careficient-transcribe",
        "extract": "careficient-extract",
        "prefill": "careficient-prefill",
        "notify": "careficient-notify",
    }
    
    @staticmethod
    def get_arn(service: str, resource: str, region: str = "us-east-1", account_id: str = "123456789012") -> str:
        """
        Construct AWS ARN.
        
        Args:
            service: AWS service
            resource: Resource identifier
            region: AWS region
            account_id: AWS account ID
        
        Returns:
            ARN string
        """
        return f"arn:aws:{service}:{region}:{account_id}:{resource}"
