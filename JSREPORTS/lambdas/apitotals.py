import requests
import json
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import logging
from util import get_secrets, get_base_url, get_api_recipient_emails, get_api_token

REGION_NAME = 'us-east-1'


def get_request_data():
    try:
        request_secrets = get_secrets('api_request_totals')

        if request_secrets is None:
            raise ValueError("api_request_totals AWS Secret not found.")

        if 'requests' not in request_secrets:
            raise ValueError("requests not found in the api_request_totals AWS secret object.")

        requests = request_secrets.get("requests")
        serialized = json.loads(requests)
        reports = serialized.get("reports")

        print(f"Reports: {reports}")
        if reports is None:
            raise ValueError("Error: no request data found")

        return reports

    except Exception as e:
        logging.error('There was a problem sending the request totals:', exc_info=True)
        raise

def get_totals(report_request):
    try:
        token = get_api_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        baseUrl = get_base_url()
        url = f"{baseUrl}/v3/reports/warranty-create"

        response = requests.get(url, json=report_request, headers=headers)
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

def send_reports_email(totals):
    try:
        data = {
            "template": {
                "name": "dlt_api_report",
            },
            "data": totals
        }

        jsecrets = get_secrets('JSREPORTS_ABEL')

        usn = jsecrets['usn']
        pwd = jsecrets['pwd']
        
        url = 'https://jsreports.afg.tech/api/report'

        response = requests.post(url, json=data, auth=(usn, pwd))
        
        if response.status_code == 200:
            print('PDF generated successfully')
            with open('/tmp/api_report.pdf', 'wb') as f:
                f.write(response.content)
            
            send_report_email_with_pdf('/tmp/api_report.pdf')
        else:
            raise ValueError(f"Error generating PDF: {response.text}")
    except Exception as e:
        logging.error('An error occurred while generating and sending the report:', exc_info=True)
        raise

def send_report_email_with_pdf(pdf_file):
    try:
        ses_client = boto3.client('ses', region_name='us-east-1')
        
        msg = MIMEMultipart()
        
        recipients = get_api_recipient_emails()
        subj = f"Dealer Lifetime API Report - {datetime.now().strftime('%m-%d-%Y')}"
        filename = f'DLT-DailyAPIReport_{datetime.now().strftime("%m-%d-%Y")}.pdf'            

        msg['Subject'] = subj
        msg['From'] = 'Dealer-Lifetime-Support@dealerlifetime.com'
                
        with open(pdf_file, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype='pdf')
            attachment.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(attachment)

        body = MIMEText('Please find the attached daily DLT API report.')
        msg.attach(body)

        response = ses_client.send_raw_email(
            Source=msg['From'],
            Destinations=recipients,
            RawMessage={'Data': msg.as_string()}
        )

        print('Email sent successfully:', response['MessageId'])
    except ClientError as e:
        error_message = f"Error sending email: {e.response['Error']['Message']}"
        print(error_message)
        raise ValueError(error_message)
    except Exception as e:
        logging.error('An error occurred while sending the email:', exc_info=True)
        raise

def send_request_totals():
    try:
        api_request_secrets = get_secrets('api_request_totals')
        print(f"secrets type: {type(api_request_secrets)}")
        should_send = api_request_secrets['send_report'].lower() == 'true'
        if should_send:

            end_date = datetime.combine(datetime.today(), datetime.min.time())
            start_date = end_date - timedelta(days=1)

            requests = get_request_data()
            for request in requests:
                request["StartDate"] = start_date.isoformat()
                request["EndDate"] = end_date.isoformat()

                totals = get_totals(request)
                if totals is None:
                    logging.error("Error: get_totals returned None")
                    continue

                today = start_date.strftime('%m/%d/%Y')
                totals['date'] = today
                send_reports_email(totals)

    except Exception as e:
        logging.error('There was a problem sending the request totals:', exc_info=True)
        raise