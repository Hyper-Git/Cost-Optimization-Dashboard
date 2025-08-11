import boto3
from datetime import datetime, timedelta

# Test the Cost Explorer API locally
ce_client = boto3.client('ce')

end_date = datetime.now().date()
start_date = end_date - timedelta(days=1)

response = ce_client.get_cost_and_usage(
    TimePeriod={
        'Start': start_date.strftime('%Y-%m-%d'),
        'End': end_date.strftime('%Y-%m-%d')
    },
    Granularity='DAILY',
    Metrics=['BlendedCost']
)

print("Yesterday's AWS costs:")
for result in response['ResultsByTime']:
    total = result['Total']['BlendedCost']['Amount']
    print(f"Total: ${float(total):.2f}")