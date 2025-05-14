import boto3
import json
import time
import os

ATHENA_DB = "oes_data"
ATHENA_TABLE = "oes_data_raw"
S3_OUTPUT = "s3://<your-athena-query-results-bucket>/"  # Replace with your bucket

athena = boto3.client('athena')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    query = f"SELECT * FROM {ATHENA_DB}.{ATHENA_TABLE} ORDER BY timestamp DESC LIMIT 1;"
    
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': ATHENA_DB},
        ResultConfiguration={'OutputLocation': S3_OUTPUT}
    )
    
    query_execution_id = response['QueryExecutionId']

    # Wait for the query to complete
    while True:
        status = athena.get_query_execution(QueryExecutionId=query_execution_id)
        state = status['QueryExecution']['Status']['State']
        if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        time.sleep(2)

    if state != 'SUCCEEDED':
        return {
            'statusCode': 500,
            'body': json.dumps('Athena query failed')
        }

    # Get query results
    results = athena.get_query_results(QueryExecutionId=query_execution_id)
    rows = results['ResultSet']['Rows']

    if len(rows) < 2:
        return {
            'statusCode': 404,
            'body': json.dumps('No data found')
        }

    # Extract headers and data row
    headers = [col['VarCharValue'] for col in rows[0]['Data']]
    values = [col['VarCharValue'] for col in rows[1]['Data']]
    result = dict(zip(headers, values))

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',  # CORS
            'Content-Type': 'application/json'
        },
        'body': json.dumps(result)
    }
