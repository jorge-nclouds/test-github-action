from datetime import datetime, timedelta
import requests
from util import get_invoice_recipient_emails, get_api_token, get_base_url
import csv
import logging
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import os
from botocore.exceptions import ClientError

def get_first_day_of_previous_month():
    today = datetime.now()

    first_day_of_current_month = today.replace(day=1)

    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)

    first_day_of_previous_month = last_day_of_previous_month.replace(day=1)

    formatted_date = first_day_of_previous_month.strftime('%Y-%m-%d')

    return formatted_date

def get_last_day_of_previous_month():
    today = datetime.now()

    first_day_of_current_month = today.replace(day=1)

    last_day =  first_day_of_current_month - timedelta(days=1)
    return last_day.strftime('%Y-%m-%d')
    
def get_invoiced_date():
    today = datetime.now()
    fifth_of_this_month = today.replace(day=5)
    return fifth_of_this_month.strftime('%Y-%m-%d') 

def fetch_dlt_invoice_data():
    try:
        token = get_api_token()

        body = {
            'startDate': get_first_day_of_previous_month(),
            'endDate': get_last_day_of_previous_month(),
            'DistributorId': '7229956a-5b35-4a1d-9925-1e5fc29e9e03',
            'MarkAsInvoiced': 'false',
            'InvoicedDate': get_invoiced_date()
        }
        
        print(body);
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        baseUrl = get_base_url()
        url = f"{baseUrl}/v3/reports/invoicing"

        response = requests.post(url, json=body, headers=headers)
        print(f"API Response: {response.status_code}")
        if response.status_code == 200:
            print(f"response! {response.content}")
            responseObj = response.json() 
            return responseObj
        else:
            raise ValueError(f"Error getting invoicing totals: {response.text}")
    except Exception as e:
        logging.error('There was a problem getting the invoicing totals:', exc_info=True)
        raise
    
def create_csv(data, csv_file_path):
    try:
        field_mapping = {
            "dealerName": "Dealer Name",
            "dealerCode": "Dealer Code",
            "programName": "Program Name",
            "roNumber": "RO Number",
            "contractNumber": "Contract Number",
            "productSKU": "Product SKU",
            "manufacturerSKU": "Manufacturer SKU",
            "productQTY": "Product QTY",
            "status": "Status",
            "dateWarrantySold": "Date Warranty Sold",
            "createdDate": "Created Date",
            "internal": "Internal",
            "customerName": "Customer Name",
            "vin": "VIN",
            "invoiceAmountDue": "Invoice Amount Due"
        }

        fieldnames = list(field_mapping.values())

        with open(csv_file_path, mode='w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                transformed_row = {field_mapping[key]: value for key, value in row.items() if key in field_mapping}
                writer.writerow(transformed_row)
        print(f"CSV file created successfully at {csv_file_path}")
    except Exception as e:
        print(f"Failed to create CSV file: {e}")
        raise

def send_email_with_csv(csv_file_path):
    try:
        ses_client = boto3.client('ses', region_name='us-east-1')
        
        msg = MIMEMultipart()
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        month_year = yesterday.strftime('%B-%Y')

        environment = os.getenv('ENV_VAR', 'dev')
        recipients = get_invoice_recipient_emails()
        
        if environment == 'production':
            subj = f'Dealer Lifetime Invoicing - {month_year}'
            fn = f'DLT-InvoiceReport_{month_year}.csv'            
        else:
            subj = f'DEV - Dealer Lifetime Invoicing - {month_year}'
            fn = f'DEV_DLT-InvoiceReport_{month_year}.csv'        
        
        msg['Subject'] = subj
        msg['From'] = 'Dealer-Lifetime-Support@dealerlifetime.com'
        
        print(f"Recipient List: {recipients}")
        
        with open(csv_file_path, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype='csv')
            attachment.add_header('Content-Disposition', 'attachment', filename=fn)
            msg.attach(attachment)

        bodystring = f'Please find the attached monthly invoice report for - {month_year}'

        body = MIMEText(bodystring)
        msg.attach(body)

        response = ses_client.send_raw_email(
            Source=msg['From'],
            Destinations=recipients,
            RawMessage={'Data': msg.as_string()}
        )

        print('Email sent successfully:', response['MessageId'])
    except ClientError as e:
        print('Error sending email:', e.response['Error']['Message'])
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_invoicing_data():
    try:
        reportData = fetch_dlt_invoice_data()
        
        if isinstance(reportData, dict) and 'invoiceRecords' in reportData:
            reportData = reportData['invoiceRecords']
        
        csv_file_path = '/tmp/invoice_report.csv'
        create_csv(reportData, csv_file_path)
        
        send_email_with_csv(csv_file_path)
    except Exception as e:
        print('An error occurred trying to send the request totals: ', str(e))

if __name__ == "__main__":
    send_invoicing_data()