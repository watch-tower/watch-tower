#!/usr/bin/python3


import sys
import json
import os
import argparse
sys.path.append('/home/gorilla/PycharmProjects/WatchTower')
sys.path.append('/home/gorilla/PycharmProjects/WatchTower/venv/lib/python3.8/site-packages')
from app.models import Inventory, Host, Variable


log = open('dynamic_hosts.log' , 'w')
for k, v in os.environ.items():
    log.write('{}={}\n'.format(k,v))

def read_cli_args():
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action = 'store_true')
        parser.add_argument('--host', action = 'store')
        args = parser.parse_args()
        return args

def main():
    try:
        args = read_cli_args()
        inventory_id = os.environ['inventory_id']
        inventory = Inventory.query.get(inventory_id)
        log.write('inventory id = {}\ninventory object = {}'.format(inventory_id, inventory))
        dick = {}
        host_names = []
        hosts = Host.query.filter_by(inventory_id=inventory.id)
        for host in hosts:
            host_names.append(host.name)
        host_vars = {}
        for host in hosts:
            vars_dict = {}
            for var in Variable.query.filter_by(host_id=host.id):
                vars_dict[var.name] = var.value
            host_vars[host.name] = vars_dict
        dick['all'] = {'hosts': host_names}
        dick['_meta'] = {'hostvars': host_vars}
        log.write('resp is {}'.format(json.dumps(dick)))
        print(json.dumps(dick))
    except Exception as e:
        log.write('fucking exception is {}'.format(str(e)))
    log.close()


if __name__ == "__main__":
    main()

