import json
import boto3
import os
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from botocore.exceptions import ClientError

REGION = 'us-west-2'
HOST = os.environ['OpenSearchDomainName']
INDEX = os.environ['OpenSearchIndex']

s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')

def lambda_handler(event, context):
    # TODO implement
    print("Lambda v1.2")
    print(event)
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    print("bucket is ",bucket)
    print("key is ",key)

    # Call Rekognition to detect labels in the image
    response = rekognition.detect_labels(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        }
    )
    
    print(response)
    
    # Get the S3 object's metadata
    s3_metadata = s3.head_object(Bucket=bucket, Key=key)
    custom_labels = s3_metadata.get('Metadata', {}).get('customlabels')
    print("s3_metadata is ",s3_metadata)
    print(s3_metadata.get('Metadata', {}))
    print("custom_labels is ",custom_labels)

    # Create the JSON object with required fields
    labels = [label['Name'] for label in response['Labels']]
    timestamp = s3_metadata['LastModified'].isoformat()
    object_key = key.split('/')[-1]
    
    data = {
        "objectKey": object_key,
        "bucket": bucket,
        "createdTimestamp": timestamp,
        "labels": labels
    }

    # If custom labels exist, add them to the 'labels' array
    if custom_labels:
        custom_labels = custom_labels.split(',')
        data["labels"].extend(custom_labels)
        
    print("JSON data is ",data)
    
    # Store the data in OpenSearch index ("photos")
    insert_data(data)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Successfully put photp from S3 to OpenSearch!')
    }

def insert_data(data):
    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
                        http_auth=get_awsauth(REGION, 'es'),
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection)
    client.index(index=INDEX, body=data)
                        
def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)