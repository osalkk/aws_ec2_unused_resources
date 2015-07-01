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

        #EIP
        client = boto3.client('ec2', region_name=region)
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



        #ELB
        client = boto3.client('elb', region_name=region)
        response = client.describe_load_balancers()
        elbs=[]
        for ELB in response['LoadBalancerDescriptions']:
            if len(ELB['Instances']) == 0:
                elbs.append(ELB['LoadBalancerName'])

        if len(elbs) > 0:
            append('<br><table><caption>Unused ELBs</caption><th>Resource</th><th>ELB Name</th>')
            for elb in elbs:
                append('<tr><td>ELB</td><td>'+elb+'</td></tr>')
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
            if ASG['LaunchConfigurationName'] in LC_list:
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


if __name__ == "__main__":
    try:
        save_cost()
        send_report()
    except Exception as err:
        print(err)
