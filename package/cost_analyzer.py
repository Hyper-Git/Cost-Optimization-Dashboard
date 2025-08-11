import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
import os

def lambda_handler(event, context):
    """
    Business Purpose: Weekly cost analysis with optimization recommendations
    Analyzes 7-day cost trends and provides actionable business insights
    """
    
    # Initialize AWS clients
    ce_client = boto3.client('ce')
    dynamodb = boto3.resource('dynamodb')
    sns_client = boto3.client('sns')
    
    # Get last 7 days of cost data
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    try:
        # Get detailed cost breakdown by service
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['BlendedCost', 'UsageQuantity'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'DIMENSION', 'Key': 'REGION'}
            ]
        )
        
        # Analyze the data
        analysis = analyze_costs(response)
        
        # Store historical data
        store_cost_data(dynamodb, analysis)
        
        # Generate recommendations
        recommendations = generate_recommendations(analysis)
        
        # Send detailed report
        send_weekly_report(sns_client, analysis, recommendations)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Weekly analysis complete',
                'total_weekly_cost': float(analysis['total_cost']),
                'top_service': analysis['top_service'],
                'recommendations_count': len(recommendations)
            })
        }
        
    except Exception as e:
        print(f"Error in cost analysis: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def analyze_costs(cost_data):
    """
    Business Logic: Analyze cost patterns and identify trends
    """
    total_cost = 0
    service_costs = {}
    daily_costs = {}
    regional_costs = {}
    
    for result in cost_data['ResultsByTime']:
        date = result['TimePeriod']['Start']
        daily_total = 0
        
        for group in result['Groups']:
            service = group['Keys'][0] if group['Keys'][0] else 'Unknown'
            region = group['Keys'][1] if len(group['Keys']) > 1 else 'Global'
            cost = float(group['Metrics']['BlendedCost']['Amount'])
            
            # Aggregate by service
            if service not in service_costs:
                service_costs[service] = 0
            service_costs[service] += cost
            
            # Aggregate by region
            if region not in regional_costs:
                regional_costs[region] = 0
            regional_costs[region] += cost
            
            total_cost += cost
            daily_total += cost
        
        daily_costs[date] = daily_total
    
    # Find top cost drivers
    top_service = max(service_costs.items(), key=lambda x: x[1]) if service_costs else ('None', 0)
    top_region = max(regional_costs.items(), key=lambda x: x[1]) if regional_costs else ('None', 0)
    
    return {
        'total_cost': total_cost,
        'service_costs': service_costs,
        'regional_costs': regional_costs,
        'daily_costs': daily_costs,
        'top_service': top_service,
        'top_region': top_region,
        'analysis_date': datetime.now().isoformat()
    }

def generate_recommendations(analysis):
    """
    Business Intelligence: Generate actionable cost optimization recommendations
    """
    recommendations = []
    
    # Recommendation 1: High-cost services
    if analysis['total_cost'] > 1.0:  # If weekly cost > $1
        top_service, top_cost = analysis['top_service']
        recommendations.append({
            'type': 'cost_optimization',
            'priority': 'high',
            'service': top_service,
            'issue': f'{top_service} accounts for ${top_cost:.2f} of your weekly costs',
            'recommendation': f'Review {top_service} usage and consider optimization',
            'potential_savings': f'Up to 30% (${top_cost * 0.3:.2f}/week)'
        })
    
    # Recommendation 2: Multi-region usage
    if len(analysis['regional_costs']) > 2:
        recommendations.append({
            'type': 'architecture',
            'priority': 'medium',
            'issue': f'Resources deployed across {len(analysis["regional_costs"])} regions',
            'recommendation': 'Consolidate resources to fewer regions to reduce data transfer costs',
            'potential_savings': 'Up to 15% in data transfer costs'
        })
    
    # Recommendation 3: Daily cost trends
    daily_costs = list(analysis['daily_costs'].values())
    if len(daily_costs) > 1:
        avg_cost = sum(daily_costs) / len(daily_costs)
        recent_cost = daily_costs[-1]
        if recent_cost > avg_cost * 1.5:
            recommendations.append({
                'type': 'monitoring',
                'priority': 'high',
                'issue': f'Recent daily cost (${recent_cost:.2f}) is 50% above average',
                'recommendation': 'Investigate recent changes in resource usage',
                'potential_savings': 'Prevent cost escalation'
            })
    
    return recommendations

def store_cost_data(dynamodb, analysis):
    """
    Business Requirement: Store historical data for trend analysis
    """
    try:
        table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'cost-analysis'))
        
        # Convert floats to Decimal for DynamoDB
        def convert_floats(obj):
            if isinstance(obj, float):
                return Decimal(str(obj))
            elif isinstance(obj, dict):
                return {k: convert_floats(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_floats(v) for v in obj]
            else:
                return obj
        
        analysis_item = convert_floats(analysis)
        analysis_item['id'] = analysis['analysis_date']
        
        table.put_item(Item=analysis_item)
        print("Cost data stored successfully")
        
    except Exception as e:
        print(f"Error storing data: {str(e)}")

def send_weekly_report(sns_client, analysis, recommendations):
    """
    Business Communication: Send actionable weekly cost report
    """
    message = "📊 Weekly AWS Cost Analysis Report\n\n"
    message += f"💰 Total Weekly Cost: ${analysis['total_cost']:.2f}\n"
    message += f"📈 Top Service: {analysis['top_service'][0]} (${analysis['top_service'][1]:.2f})\n"
    message += f"🌍 Top Region: {analysis['top_region'][0]} (${analysis['top_region'][1]:.2f})\n\n"
    
    if recommendations:
        message += "🎯 Optimization Recommendations:\n\n"
        for i, rec in enumerate(recommendations[:3], 1):  # Top 3 recommendations
            message += f"{i}. [{rec['priority'].upper()}] {rec['type'].title()}\n"
            message += f"   Issue: {rec['issue']}\n"
            message += f"   Action: {rec['recommendation']}\n"
            message += f"   Savings: {rec['potential_savings']}\n\n"
    
    message += "📋 Service Breakdown:\n"
    sorted_services = sorted(analysis['service_costs'].items(), key=lambda x: x[1], reverse=True)
    for service, cost in sorted_services[:5]:  # Top 5 services
        if cost > 0:
            percentage = (cost / analysis['total_cost']) * 100 if analysis['total_cost'] > 0 else 0
            message += f"• {service}: ${cost:.2f} ({percentage:.1f}%)\n"
    
    try:
        sns_client.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Message=message,
            Subject=f"Weekly Cost Analysis: ${analysis['total_cost']:.2f}"
        )
        print("Weekly report sent successfully")
    except Exception as e:
        print(f"Error sending report: {str(e)}")