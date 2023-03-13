import json
import json, csv
import meraki

def lambda_handler(event, context):
    
    api_key = ""
    data = {}
    
    if event["api_key"]:
        api_key = event["api_key"]
    else:
        return
    
    if event["data"]:
        data = event["data"]
    else:
        return
        
    dashboard = meraki.DashboardAPI(
        api_key,
        output_log=False,
        print_console=False,
    )
        
    response_from_meraki = dashboard.appliance.createNetworkApplianceStaticRoute(data["network_id"], data["name"], data["subnet"], data["gateway_ip"])
    
    return {
        'statusCode': 200,
        'body': json.dumps(response_from_meraki)
    }
