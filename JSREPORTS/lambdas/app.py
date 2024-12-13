import datetime
from apitotals import send_request_totals
from dailySales import fetch_dlt_sales_data, generate_and_send_report
from invoicing import send_invoicing_data
def lambda_handler(event, context):
    #Daily Sales Report
    try:
        dlt_df = fetch_dlt_sales_data()
        if dlt_df is None:
            raise ValueError("Failed to fetch DLT sales data")

        if dlt_df is None:
            raise ValueError("Failed to fetch DLT sales total data")

        generate_and_send_report(dlt_df)

    except Exception as e:
        print('An error occurred trying to send the request totals: ', str(e))

    # API Report
    try:
        send_request_totals()
    except Exception as e:
        print('An error occured trying to send the api request totals: ', str(e))


    #Invoicing Report
    # try:
    #     today = datetime.now()
    #     if(today.day == 1):
    #         send_invoicing_data()
    #     else: 
    #         print('today is not the first. Not sending invoice report.');
    # except Exception as e:
    #     print('An error occured trying to send the api request totals: ', str(e))
    
if __name__ == "__main__":
    lambda_handler(None, None)
