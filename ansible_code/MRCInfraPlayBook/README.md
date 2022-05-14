Execute below command to run the playbook (from under MRCInfraPlayBook directory after cloning):
        . ./Team14_openrc.sh ; ansible-playbook DeployInfra_playbook.yaml 
When prompted to OPENSTACK PASSWORD, enter the password from APIPassword.txt which is not in this repository



To copy files from localhost to remote host DB Servers:
1. Ensure the files that need to be copied are under MRCInfraPlayBook/roles/Database_Level/files/
2. Update the task file MRCInfraPlayBook/roles/Database_Level/tasks/load_data.yaml by including a command to copy using existing sample as reference 

To copy files from localhost to remote host App Servers:
1. Ensure the files that need to be copied are under MRCInfraPlayBook/roles/AppServer_Level/files/
2. Update the task file MRCInfraPlayBook/roles/AppServer_Level/tasks/main.yaml by including a command to copy using existing sample as reference 
