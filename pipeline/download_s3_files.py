#!/usr/bin/python3
"""
Download files pertaining to a particular study from the Beiwe Data Access API. The relevant
AWS object names and study information are passed as environment variables.
"""

import os

import boto3
import requests


# Grab environment variables
freq = os.getenv('FREQ')
access_key_ssm_name = '{}-{}'.format(os.getenv('access_key_ssm_name'), freq)
secret_key_ssm_name = '{}-{}'.format(os.getenv('secret_key_ssm_name'), freq)
study_object_id = os.getenv('study_object_id')
region_name = os.getenv('region_name')
server_url = os.getenv('server_url')

# Get the necessary credentials for pinging the Beiwe server
ssm_client = boto3.client('ssm', region_name=region_name)
resp = ssm_client.get_parameters(
    Names=(access_key_ssm_name, secret_key_ssm_name),
    WithDecryption=True,
)['Parameters']
access_key, secret_key = [p['Value'] for p in resp]

data_access_api_url = '{}/get-data/v1'.format(server_url)

payload = {
    'access_key': access_key,
    'secret_key': secret_key,
    'study_id': study_object_id,
}
# TODO do this as a generator, if simple
resp = requests.post(data_access_api_url, data=payload)
byte_stream = resp.content
with open('study-data.zip', 'xb') as fn:
    fn.write(byte_stream)
