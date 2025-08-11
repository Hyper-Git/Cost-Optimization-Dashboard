import boto3
import json
from datetime import datetime, timedelta
import os

def lambda_handler(event, context):
    """
    Business Purpose: Daily cost monitoring to prevent surprise bills
    This function checks yesterday's AWS costs and alerts if over threshold
    """
    
    # Initialize AWS clients
    ce_client = boto3.client('ce')  # Cost Explorer
    sns_client = boto3.client('sns')
    
    # Get yesterday's costs (business requirement: daily monitoring)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=1)
    
    try:
        # Query Cost Explorer API
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )
        
        # Process the cost data
        daily_cost = 0
        service_costs = {}
        
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                service_costs[service] = cost
                daily_cost += cost
        
        # Business logic: Alert if over threshold
        threshold = float(os.environ.get('COST_THRESHOLD', '5.0'))  # $5 default
        
        if daily_cost > threshold:
            message = f"⚠️ AWS Cost Alert!\n\n"
            message += f"Yesterday's total: ${daily_cost:.2f}\n"
            message += f"Threshold: ${threshold:.2f}\n\n"
            message += "Top services:\n"
            
            # Sort services by cost
            sorted_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)
            for service, cost in sorted_services[:5]:
                if cost > 0:
                    message += f"• {service}: ${cost:.2f}\n"
            
            # Send alert
            sns_client.publish(
                TopicArn=os.environ['SNS_TOPIC_ARN'],
                Message=message,
                Subject=f"AWS Cost Alert: ${daily_cost:.2f}"
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Alert sent',
                    'daily_cost': daily_cost,
                    'threshold_exceeded': True
                })
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Cost within threshold',
                'daily_cost': daily_cost,
                'threshold_exceeded': False
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }