import os
import requests
import json
from util import get_secrets, get_recipient_emails, get_api_token, get_base_url
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import logging


def fetch_dlt_sales_data():
    try:
        token = get_api_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        baseUrl = get_base_url()
        url = f"{baseUrl}/v3/reports/daily-sales"

        response = requests.get(url, headers=headers)
        print(f"API Response: {response.status_code}")
        if response.status_code == 200:
            print(f"response! {response.content}")
            responseObj = json.loads(response.content)
            return responseObj
        else:
            raise ValueError(f"Error getting report totals: {response.text}")
    except Exception as e:
        logging.error('There was a problem getting the report totals:', exc_info=True)
        raise

def generate_and_send_report(dlt_df):
    try:
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        formatted_yesterday = yesterday.strftime('%Y-%m-%d')
        month_year = today.strftime('%B, %Y')
        
        
        data = {
            "template": {
                "name": "dlt_daily_sales",
            },
            "data": {
                "dlt_data": dlt_df,
                "yesterday": formatted_yesterday,
                "header": f"Warranties created for {month_year}."
            }
        }


        jsecrets = get_secrets('JSREPORTS_ABEL')

        usn = jsecrets['usn']
        pwd = jsecrets['pwd']
        
        url = 'https://jsreports.afg.tech/api/report'

        response = requests.post(url, json=data, auth=(usn, pwd))
        
        if response.status_code == 200:
            print('PDF generated successfully')
            with open('/tmp/report.pdf', 'wb') as f:
                f.write(response.content)
            
            # send pdf in email using aws ses with this identity/domain dealerlifetime.com
            send_email_with_pdf('/tmp/report.pdf')
        else:
            print('Error generating PDF:', response.text)
    except Exception as e:
        print('An error occurred while generating and sending the report:', str(e))

def send_email_with_pdf(pdf_file):
    try:
        ses_client = boto3.client('ses', region_name='us-east-1')
        
        msg = MIMEMultipart()


        environment = os.getenv('ENV_VAR', 'dev')
        recipients = get_recipient_emails()
        
        if environment == 'production':
            subj = 'Dealer Lifetime Sales - ' + datetime.now().strftime('%m-%d-%Y')
            recipients = recipients
            fn = f'DLT-DailySalesReport_{datetime.now().strftime("%m-%d-%Y")}.pdf'            
        else:
            subj = 'DEV - Dealer Lifetime Sales - ' + datetime.now().strftime('%m-%d-%Y')
            recipients = recipients         
            fn = f'DEV_DLT-DailySalesReport_{datetime.now().strftime("%m-%d-%Y")}.pdf'        
        
        msg['Subject'] = subj
        msg['From'] = 'Dealer-Lifetime-Support@dealerlifetime.com'
        
        print(f"Recipient List: {recipients}")
        
        # Attach the PDF file
        with open(pdf_file, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype='pdf')
            attachment.add_header('Content-Disposition', 'attachment', filename=fn)
            msg.attach(attachment)

        # Add a plain text message body
        body = MIMEText('Please find the attached daily DLT sales report.')
        msg.attach(body)

        response = ses_client.send_raw_email(
            Source=msg['From'],
            Destinations=recipients,
            RawMessage={'Data': msg.as_string()}
        )

        print('Email sent successfully:', response['MessageId'])
    except ClientError as e:
        print('Error sending email:', e.response['Error']['Message'])
        