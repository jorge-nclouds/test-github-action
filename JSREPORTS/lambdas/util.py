import os
import json
import boto3
import logging
import requests


REGION_NAME = 'us-east-1' 

def get_base_url():
    return "https://api.app.dealerlifetime.com"

def get_secrets(secret_name):
    """Fetch secrets from AWS Secrets Manager."""
    secretsmanager_client = boto3.client('secretsmanager', region_name=REGION_NAME)
    secret = secretsmanager_client.get_secret_value(SecretId=secret_name)
    return json.loads(secret['SecretString'])

def get_recipient_emails(): 
    try: 
        recipient_secrets = get_secrets('DLT_reporting_recipients_list')
        if not isinstance(recipient_secrets, dict):
            logging.error("Error: recipient_secrets is not a dictionary")
            return []

        environment = os.getenv('ENV_VAR', 'dev')
        
        if environment == 'production':
            return recipient_secrets['DLT_reporting_recipients'].split(',')
        else:
            return recipient_secrets['DLT_reporting_recipients_dev'].split(',')
    except Exception as e:
        print(f"Error fetching recipient emails: {e}")
        return []
    
    
def get_invoice_recipient_emails(): 
    try: 
        recipient_secrets = get_secrets('DLT_invoicing_recipients_list')
        if not isinstance(recipient_secrets, dict):
            logging.error("Error: recipient_secrets is not a dictionary")
            return []

        environment = os.getenv('ENV_VAR', 'dev')

        if environment == 'production':
            return recipient_secrets['DLT_invoicing_recipients'].split(',')
        else:
            return recipient_secrets['DLT_invoicing_recipients_dev'].split(',')
    except Exception as e:
        print(f"Error fetching invoicing emails: {e}")
        return []

def get_api_recipient_emails(): 
    try: 
        recipient_secrets = get_secrets('DLT_API_Counts_Recipients')
        if not isinstance(recipient_secrets, dict):
            logging.error("Error: recipient_secrets is not a dictionary")
            return []

        environment = os.getenv('ENV_VAR', 'dev')

        if environment == 'production':
            return recipient_secrets['recipients'].split(',')
        else:
            return recipient_secrets['recipients_dev'].split(',')
    except Exception as e:
        print(f"Error fetching API recipient emails: {e}")
        return []

def get_api_token():
    try:
        request_secrets = get_secrets('api_request_totals')

        body = {
            "email": request_secrets.get("api_email"),
            "password": request_secrets.get("api_password")
        }
     
        baseUrl = get_base_url()
        url = f"{baseUrl}/v3/identity/token"

        response = requests.post(url, json=body)
        
        if response.status_code == 200:
            print(f"retrieved api token!")
            responseObj = json.loads(response.content)
            return responseObj.get("token")
        else:
            print('Error getting API token:', response.text)

    except Exception as e:
        logging.error('There was a problem trying to get the api token:', exc_info=True)