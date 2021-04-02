#!/usr/bin/python3


import json
import sys
import os
import subprocess
import io


def build_cmd(request):
    inventory = request.get('inventory', '')
    playbook = request.get('playbook', '')
    extra_vars = request.get('extra_vars', dict())
    cmd = 'ansible-playbook playbooks/{} -i hosts'.format(playbook)
    options = []
    for arg in extra_vars:
        options.append('{}="{}"'.format(arg, extra_vars[arg]))
    join = ' '.join(options)
    if len(join) != 0:
        cmd = "{} -e '{}'".format(cmd, join)
    return cmd


def main():
    request = json.loads(input())
    cmd = build_cmd(request)
    os.environ['inventory'] = request.get('inventory')
    ansible = subprocess.Popen(cmd, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.join(os.getcwd(), 'ansible'))
    reader = io.TextIOWrapper(ansible.stdout, encoding='utf-8')
    while True:
        data = reader.read(256)
        if not data:
            break
        print(json.dumps({'data': data}))
    rc = ansible.poll()
    print(json.dumps({'code': rc}))


if __name__ == "__main__":
    main()
