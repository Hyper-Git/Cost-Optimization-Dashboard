import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

def lambda_handler(event, context):
    """
    Business Purpose: RESTful API for cost dashboard
    Provides real-time cost data for web dashboard consumption
    """
    
    # Enable CORS for web dashboard
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
    }
    
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        endpoint = event.get('pathParameters', {}).get('endpoint', 'current')
        
        ce_client = boto3.client('ce')
        
        # Route to different endpoints
        if endpoint == 'current':
            data = get_current_costs(ce_client)
        elif endpoint == 'weekly':
            data = get_weekly_costs(ce_client)
        elif endpoint == 'services':
            data = get_service_breakdown(ce_client)
        elif endpoint == 'regions':
            data = get_regional_breakdown(ce_client)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(data, default=decimal_default)
        }
        
    except Exception as e:
        print(f"API Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def get_current_costs(ce_client):
    """Get today's and yesterday's costs for real-time dashboard"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=2)
    
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date.strftime('%Y-%m-%d'),
            'End': end_date.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',
        Metrics=['BlendedCost']
    )
    
    daily_costs = []
    total_cost = 0
    
    for result in response['ResultsByTime']:
        date = result['TimePeriod']['Start']
        cost = float(result['Total']['BlendedCost']['Amount'])
        daily_costs.append({
            'date': date,
            'cost': cost
        })
        total_cost += cost
    
    return {
        'total_cost': total_cost,
        'daily_costs': daily_costs,
        'last_updated': datetime.now().isoformat()
    }

def get_weekly_costs(ce_client):
    """Get last 7 days of costs for trend analysis"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date.strftime('%Y-%m-%d'),
            'End': end_date.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',
        Metrics=['BlendedCost']
    )
    
    weekly_costs = []
    total_weekly = 0
    
    for result in response['ResultsByTime']:
        date = result['TimePeriod']['Start']
        cost = float(result['Total']['BlendedCost']['Amount'])
        weekly_costs.append({
            'date': date,
            'cost': cost
        })
        total_weekly += cost
    
    return {
        'weekly_total': total_weekly,
        'daily_breakdown': weekly_costs,
        'average_daily': total_weekly / len(weekly_costs) if weekly_costs else 0
    }

def get_service_breakdown(ce_client):
    """Get cost breakdown by AWS service - FIXED VERSION"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date.strftime('%Y-%m-%d'),
            'End': end_date.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',  # Fixed: Changed from WEEKLY to DAILY
        Metrics=['BlendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )
    
    services = {}
    total_cost = 0
    
    # Aggregate costs across all days
    for result in response['ResultsByTime']:
        for group in result['Groups']:
            service = group['Keys'][0] if group['Keys'][0] else 'Unknown'
            cost = float(group['Metrics']['BlendedCost']['Amount'])
            if cost > 0:
                if service not in services:
                    services[service] = 0
                services[service] += cost
                total_cost += cost
    
    # Convert to list and sort
    service_list = []
    for service, cost in services.items():
        service_list.append({
            'service': service,
            'cost': cost,
            'percentage': (cost / total_cost * 100) if total_cost > 0 else 0
        })
    
    service_list.sort(key=lambda x: x['cost'], reverse=True)
    
    return {
        'total_cost': total_cost,
        'services': service_list[:10]  # Top 10 services
    }

def get_regional_breakdown(ce_client):
    """Get cost breakdown by AWS region - FIXED VERSION"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date.strftime('%Y-%m-%d'),
            'End': end_date.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',  # Fixed: Changed from WEEKLY to DAILY
        Metrics=['BlendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'REGION'}]
    )
    
    regions = {}
    total_cost = 0
    
    # Aggregate costs across all days
    for result in response['ResultsByTime']:
        for group in result['Groups']:
            region = group['Keys'][0] if group['Keys'][0] else 'Global'
            cost = float(group['Metrics']['BlendedCost']['Amount'])
            if cost > 0:
                if region not in regions:
                    regions[region] = 0
                regions[region] += cost
                total_cost += cost
    
    # Convert to list and sort
    region_list = []
    for region, cost in regions.items():
        region_list.append({
            'region': region,
            'cost': cost,
            'percentage': (cost / total_cost * 100) if total_cost > 0 else 0
        })
    
    region_list.sort(key=lambda x: x['cost'], reverse=True)
    
    return {
        'total_cost': total_cost,
        'regions': region_list[:10]  # Top 10 regions
    }

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError
