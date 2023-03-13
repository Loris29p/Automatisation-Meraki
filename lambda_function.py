from __future__ import print_function
import boto3
import time
import json, csv
import meraki

s3 = boto3.client('s3')
client = boto3.client('lambda')

def CsvDataToTable(data):
    table = []
    lines = data.splitlines()
    reader = csv.DictReader(lines)
    for row in reader:
        table.append(row)
    return table

def GenerateNewFileName():
    return "logs_" + str(int(time.time())) + ".txt"

def lambda_handler(event, context):
    # TODO implement
    source_bucket = event['Records'][0]['s3']['bucket']['name']

    # get the content of the file
    file_obj = event['Records'][0]
    file_name = str(file_obj['s3']['object']['key'])
    file_obj = s3.get_object(Bucket=source_bucket, Key=file_name)
    file_content = file_obj["Body"].read().decode('utf-8')

    api_key = file_name.split('-')[1]
    mail_demandeur = file_name.split('-')[2]
    
    if not api_key:
        print("You must fill in the API key in the file name.")
        return

    if not api_key.isalnum():
        print("The API key is not valid.")
        return

    if len(api_key) < 35 or len(api_key) > 45:
        print("The API key is not valid.")
        return

    if not mail_demandeur:
        print("You must fill in the mail demandeur in the file name.")
        return

    mail_demandeur = mail_demandeur.replace("_", "@")
    mail_demandeur = mail_demandeur.replace(".csv", "")

    if not "@" in mail_demandeur:
        print("The mail demandeur is not valid.")
        return

    if not mail_demandeur.endswith(".com"):
        print("The mail demandeur is not valid.")
        return

    file_table = CsvDataToTable(file_content)
    new_file_content = ""
    data = {}

    dashboard = meraki.DashboardAPI(
        api_key,
        output_log=False,
        print_console=False,
    )

    all_static_routes = dashboard.appliance.getNetworkApplianceStaticRoutes(file_table[0]["network_id"])
    all_subnet = []
    response = []
    for static_route in all_static_routes:
        subnet = static_route["subnet"]
        all_subnet.append(subnet)
        

    for row in file_table:
        data = {
            "network_id": row["network_id"],
            "name": row["name"],
            "subnet": row["subnet"],
            "gateway_ip": row["gateway_ip"]
        }

        if "name" not in data or "subnet" not in data or "gateway_ip" not in data or "network_id" not in data:
            responseFromChild = "You must fill in all fields in the CSV file. (name, subnet, gateway_ip, network_id)"
            response.append(responseFromChild)
        else:
            if data["subnet"] not in all_subnet:
                date2send = {
                    "api_key": api_key,
                    "data": data
                }
    
                responseLambda = client.invoke(
                    FunctionName = 'arn:aws:lambda:eu-west-3:120596551477:function:meraki-actions',
                    InvocationType = 'RequestResponse',
                    Payload = json.dumps(date2send)
                )
                 
                responseFromChild = json.load(responseLambda['Payload'])
                
                response.append(responseFromChild)
            else:
                responseFromChild = "The subnet " + data["subnet"] + " already exists."
                response.append(responseFromChild)

    new_file_content = "---------------------------------------------------------------------\nDemandeur : \n---------------------------------------------------------------------\n"+ mail_demandeur +"\n\n---------------------------------------------------------------------\nFichier fournit : \n---------------------------------------------------------------------\n" + file_content + "\n\n---------------------------------------------------------------------\nRéponse de l'API : \n---------------------------------------------------------------------\n" + str(response)
    # copy the file to target bucket
    target_bucket = 'cisco-meraki-upload'
    target_folder = 'logs'
    target_name_file = GenerateNewFileName()
    target_file = target_folder + "/" + target_name_file
    s3.put_object(Bucket=target_bucket, Key=target_file, Body=new_file_content)
    print("File copied to target bucket (", target_file, ")")
    
    s3.delete_object(Bucket=source_bucket, Key=file_name)
    print("File deleted from source bucket (", file_name, ")")

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }