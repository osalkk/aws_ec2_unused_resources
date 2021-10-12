#!/usr/bin/python3
import boto3

region_list = ['eu-west-1', 'eu-central-1', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'sa-east-1']
owner_id = 'your_account_id'
filename = 'report.html'

def send_report():

    with open (filename, "r") as myfile:
        data=myfile.read().replace('\n', '')

    client = boto3.client('ses', region_name='eu-west-1') #Choose which region you want to use SES
    response = client.send_email(
        Source='me@example.com',
        Destination={
            'ToAddresses':  ['you@example.com'
            ]
        },
        Message={
            'Subject': {
            'Data': 'Unused AWS EC2 Resources'
        },
        'Body': {
            'Html': {
                'Data': data
            }
        }

        }
    )


def append(text):
        with open(filename, "a") as f:
            f.write(text+'\n')
            f.close()


def save_cost():
    html = """\
            <html>
              <head>
              <style>
              h1 {
	text-shadow: 0px 1px 1px #4d4d4d;
	color: #222;
	font: 40px 'LeagueGothicRegular';
}
                table, th, td {
                    border: 1px solid black;
                    background-color: #f1f1c1;
                    table-layout: fixed;
                    width:100%;
                }
                caption, th, td {
  padding: .2em .8em;
  border: 1px solid #fff;
}

caption {
  background: #dbb768;
  font-weight: bold;
  font-size: 1.1em;
}

th {
  font-weight: bold;
  background: #f3ce7d;
}

td {
  background: #ffea97;
}</style>
</head>
              <body>
              """
    with open(filename, "w") as f:
        f.write(html+'\n')
        f.close()

    for region in region_list:
        append('<h1 style="color:red"><center>'+region+'</center></h1>')

        client = boto3.client('ec2', region_name=region)

        #EIP
        response = client.describe_addresses()
        eips=[]
        for address in response['Addresses']:
            if 'InstanceId' not in address:
                eips.append(address['PublicIp'])
        if len(eips) > 0:
            append('<br><table><caption>Disassociated EIPS</caption><tr><th>Resource</th><th>Ip Address</th>')
            for eip in eips:
                append('<tr><td>EIP</td><td>'+eip+'</td></tr>')
            append('</table>')

        #Volumes
        response=client.describe_volumes()

        volumes = []
        for volume in response['Volumes']:
            if len(volume['Attachments']) == 0:
                volume_dict = {}
                volume_dict['VolumeId'] = volume['VolumeId']
                volume_dict['VolumeType'] = volume['VolumeType']
                volume_dict['VolumeSize'] = volume['Size']
                volumes.append(volume_dict)
        if len(volumes) > 0:
            append('<br><table><caption>Unattached Volumes</caption><th>Resource</th><th>Volume ID</th><th>Volume Type</th><th>Volume Size</th>')
            for vol in volumes:
                append('<tr><td>Volume </td><td>'+vol['VolumeId']+'</td><td>'+vol['VolumeType']+'</td><td>'+str(vol['VolumeSize'])+'GB</td></tr>')
        append('</table>')

        #Snapshots
        response = client.describe_snapshots(OwnerIds=[owner_id])
        snapshots=[]
        for snapshot in response['Snapshots']:
            if 'ami' not in snapshot['Description']:
                snapshots.append(snapshot['SnapshotId'])

        if len(snapshots) > 0:
            append('<br><table><caption>Unused Snaphosts</caption><th>Resource</th><th>Snapshot ID</th>')
            for snap in snapshots:
                append('<tr><td>Snapshot</td><td>'+snap+'</td></tr>')
            append('</table>')


        #Securit Groups
        response = client.describe_security_groups()
        all_sec_groups = []
        for SecGrp in response['SecurityGroups']:
            all_sec_groups.append(SecGrp['GroupName'])

        sec_groups_in_use = []
        response = client.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': ['running', 'stopped']
                }
            ])

        for r in response['Reservations']:
            for inst in r['Instances']:
                if inst['SecurityGroups'][0]['GroupName'] not in sec_groups_in_use:
                    sec_groups_in_use.append(inst['SecurityGroups'][0]['GroupName'])

        unused_sec_groups = []

        for groups in all_sec_groups:
            if groups not in sec_groups_in_use:
                unused_sec_groups.append(groups)

        if len(unused_sec_groups) > 0:
            append('<br><table><caption>Unused Security Groups</caption><th>Resource</th><th>Security Group Name</th>')
            for sg in unused_sec_groups:
                append('<tr><td>Security Group</td><td>'+sg+'</td></tr>')
        append('</table>')

        #ELBv1
        client = boto3.client('elb', region_name=region)
        response = client.describe_load_balancers()
        elbs=[]
        for ELB in response['LoadBalancerDescriptions']:
            if len(ELB['Instances']) == 0:
                elbs.append(ELB['LoadBalancerName'])

        if len(elbs) > 0:
            append('<br><table><caption>Unused Classic ELBs</caption><th>Resource</th><th>ELB Name</th>')
            for elb in elbs:
                append('<tr><td>ELB</td><td>'+elb+'</td></tr>')
        append('</table>')

        #Ami's
        client = boto3.client('ec2', region_name=region)
        
        instances = client.describe_instances()
        used_amis = []
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                used_amis.append(instance['ImageId'])
        
        custom_images = client.describe_images(
            Filters=[
                   {
                   'Name': 'state',
                   'Values': [
                       'available'
                   ]
               },
            ],
            Owners= ['self']
        )
        
        custom_amis_list = []

        for image in custom_images['Images']:
            custom_amis_list.append(image['ImageId'])
        
        if len(custom_amis_list) > 0:
            for custom_ami in custom_amis_list:
                if custom_ami not in used_amis:
                    append('<br><table><caption>Unused AMIs</caption><th>Resource</th><th>AMI Id/th>')
                    for ami in custom_amis_list:
                        append('<tr><td>AMI</td><td>'+ami+'</td></tr>')
        append('</table>')
            
        #ELBv2
        client = boto3.client('elbv2', region_name=region)
        
        response_targets = client.describe_target_groups()
        response_lbs = client.describe_load_balancers()
        
        elbsv2_arns=[]
        elbsv2_target_arns=[]
        
        elbsv2_unused=[]
        elbsv2_unhealthy=[]
        elbsv2_nolisteners=[]

        #ELBv2 check Target groups
        for tg in response_targets['TargetGroups']:
                elbsv2_target_arns.append(tg['TargetGroupArn'])
        
        for target_group in elbsv2_target_arns:
            response_healthy = client.describe_target_health(TargetGroupArn=target_group)
            for target in response_healthy['TargetHealthDescriptions']:
                if target['TargetHealth']['State'] == "unused" :
                    elbsv2_unused.append(target_group)
                elif target['TargetHealth']['State'] == "unhealthy" :
                    elbsv2_unhealthy.append(target_group)

        #ELBv2 check Load Balancers without Listeners
        for ELB in response_lbs['LoadBalancers']:
            elbsv2_arns.append(ELB['LoadBalancerArn'])
        
        for ELB in elbsv2_arns:
            response_listeners = client.describe_listeners(LoadBalancerArn=ELB) 
            if response_listeners['Listeners'] == []:
                elbsv2_nolisteners.append(ELB)
        
        # Fill HTML ELBsv2
        if len(elbsv2_unused) > 0:
            append('<br><table><caption>Unused Target Groups</caption><th>Resource</th><th>ELB Name</th>')
            for elbv2 in elbsv2_unused:
                append('<tr><td>ELB</td><td>'+elbv2+'</td></tr>')
        append('</table>')

        if len(elbsv2_unhealthy) > 0:
            append('<br><table><caption>Unhealthy Target Groups</caption><th>Resource</th><th>ELB Name</th>')
            for elbv2 in elbsv2_unhealthy:
                append('<tr><td>ELB</td><td>'+elbv2+'</td></tr>')
        append('</table>')
        
        if len(elbsv2_nolisteners) > 0:
            append('<br><table><caption>LoadBalancer with no Listeners</caption><th>Resource</th><th>ELB Name</th>')
            for elbv2 in elbsv2_nolisteners:
                append('<tr><td>ELB</td><td>'+elbv2+'</td></tr>')
        append('</table>')

        #RDS
        client = boto3.client('rds', region_name=region)
        response = client.describe_db_instances()
        rds_instances = []
        unused_rds_instances = []
        
        for rds in response['DBInstances']:
            rds_instances.append(rds['DBInstanceIdentifier'])
              #rds_instances(rds['DBInstanceIdentifier']) += rds['Endpoint']['Address']
        
        # cloudwatch (check last connections RDS)
        client_cloudwatch = boto3.client('cloudwatch', region_name=region)

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        # Getting DatabaseConnections metrics for the last 30 days
        for db in rds_instances:
            connection_statistics = client_cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='DatabaseConnections',
            Dimensions=[
                {
                'Name': 'DBInstanceIdentifier',
                'Value': db
                },
            ],
            StartTime=start_date,
            EndTime=end_date,
            Period=86400,
            Statistics=["Maximum"]
            )

            total_connection_count = sum(data_point['Maximum']
                                 for data_point in connection_statistics['Datapoints'])

            if total_connection_count == 0:
                unused_rds_instances.append(db)

        # Fill HTML RDS
        if len(unused_rds_instances) > 0:
            append('<br><table><caption>Unused RDS Instances (No connection last 30 days)</caption><th>Resource</th><th>RDS DB</th>')
            for rds in unused_rds_instances:
                append('<tr><td>RDS</td><td>'+rds+'</td></tr>')
        append('</table>')

        #Autoscaling
        client = boto3.client('autoscaling', region_name=region)
        response = client.describe_launch_configurations()
        LC_list=[]
        for LC in response['LaunchConfigurations']:
            LC_name = LC['LaunchConfigurationName']
            LC_list.append(LC_name)
        response1 = client.describe_auto_scaling_groups()
        for ASG in response1['AutoScalingGroups']:
            if ASG.get('LaunchConfigurationName') in LC_list:
                    LC_list.remove(ASG['LaunchConfigurationName'])
        LCs=[]
        for LC in LC_list:
            LCs.append(LC)

        if len(LCs) > 0:
            append('<br><table><caption>Unused Launch Configurations</caption><th>Resource</th><th>LC Name</th>')
            for lc in LCs:
                append('<tr><td>LC</td><td>'+lc+'</td></tr>')
        append('</table>')

        response = client.describe_auto_scaling_groups()
        ASGs=[]
        for ASG in response['AutoScalingGroups']:
            if ASG['DesiredCapacity'] == 0:
                ASGs.append(ASG['AutoScalingGroupName'])

        if len(ASGs) > 0:
            append('<br><table><caption>Unused Auto Scaling Groups</caption><th>Resource</th><th>ASG Name</th>')
            for asg in ASGs:
                append('<tr><td>ASG</td><td>'+asg+'</td></tr>')
        append('</table>')

    html = """\
              </body>
              </html>
              """
    with open(filename, "a") as f:
        f.write(html+'\n')
        f.close()


def lambda_handler(event, context):
    try:
        save_cost()
        send_report()
    except Exception as err:
        print(err)
