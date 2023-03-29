import subprocess
from flask import Flask, Response
from multiprocessing import Process, Manager

servers = {
    'server1': {
        'service': 'SBSUI',
        'day': 'day0',
    },
    'server2': {
        'service': 'SBSUI',
        'day': 'day0'
    },
    'server3': {
        'service': 'SBSUI',
        'day': 'day1'
    },
    'server4': {
        'service': 'EBWS',
        'day': 'day2'
    },
    'server5': {
        'service': 'SIMUI',
        'day': 'day3'
    }
}

app = Flask(__name__)

def get_command_output(server, cmd):
    ssh_cmd = f"ssh {server} '{cmd}'"
    process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return output.decode('utf-8')

def get_block_size_and_date(output):
    split_output = output.strip().split(' ')
    block_size = split_output[0]
    deploy_date = ' '.join(split_output[1:])
    return block_size, deploy_date

def get_server_data(server, results):
    deploy_version = get_command_output(server, "ls -l /root/home | grep deploy | awk '{print $2}'")
    profile_version = get_command_output(server, "ls -l /root/home/was | grep profiles | awk '{print $2}'")
    deploy_output = get_command_output(server, "ls -l /root/home | grep deploy | awk '{print $2, $3, $4, $5}'")
    deploy_block_size, deploy_date = get_block_size_and_date(deploy_output)

    profile_output = get_command_output(server, "ls -l /root/home/was855 | grep profiles | awk '{print $2, $3, $4, $5}'")
    profile_block_size, profile_date = get_block_size_and_date(profile_output)

    data = {
        'server': server,
        'service': servers[server]['service'],
        'day': servers[server]['day'],
        'deploy_version': deploy_version,
        'profile_version': profile_version,
        'deploy_block_size': deploy_block_size,
        'deploy_date': deploy_date,
        'profile_block_size': profile_block_size,
        'profile_date': profile_date,
        'match': deploy_block_size == profile_block_size
    }

    results.append(data)

@app.route('/versions')
def get_data():
    manager = Manager()
    results = manager.list()

    processes = []
    for server in servers:
        process = Process(target=get_server_data, args=(server, results))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    output = []
    for result in results:
        labels = f'service="{result["service"]}",day="{result["day"]}",server="{result["server"]}"'
        output.append(f'sbs_deploy_block_size{{{labels}}} {result["deploy_block_size"]}')
        output.append(f'sbs_deploy_date{{{labels}}} {result["deploy_date"]}')
        output.append(f'sbs_profile_block_size{{{labels}}} {result["profile_block_size"]}')
        output.append(f'sbs_profile_date{{{labels}}} {result["profile_date"]}')
        output.append(f'sbs_match{{{labels}}} {int(result["match"])}')

    return Response('\n'.join(output), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True)
