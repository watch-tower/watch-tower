from flask import send_file
from flask import Response
from app import *
from app.models import Inventory, Host, Variable
from datetime import datetime

import json
import shortuuid
import os
import subprocess
import io
import magic
import jsonschema


@app.route('/index')
def index():
    return send_file('/home/gorilla/PycharmProjects/WatchTower/templates/index.html')


ANSIBLE_INSTANCES = {}
@app.route('/prepare', methods=['POST'])
def prepare():
    request_data = request.get_json(force=True, silent=True)
    if request_data == None:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    schema = {
        "type" : "object",
        "properties" : {
            "inventory_id" : {"type" : "number"},
            "playbook" : {"type" : "string"},
            "log" : {"type" : "string"},
            "extra_vars" : {"type" : "object"}
        },
        "required" : ["inventory_id", "playbook"]
    }
    try:
        jsonschema.validate(schema=schema, instance=request_data)
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    if not os.path.exists(os.path.join(play_dir, request_data['playbook'])):
        return jsonify({'success' : 0, 'error' : 'playbook {} is not present in play directory'.format(request_data['playbook'])})
    if not Inventory.query.get(request_data['inventory_id']):
        return jsonify({'success' : 0, 'error' : 'inventory not found'})
    uuid = shortuuid.ShortUUID().random(length=10).lower()
    def stream():
        # --extra-vars=%s
        # use @json_file instead %s
        cmd = 'ansible-playbook play/%s -i dynamic_hosts.py --extra-vars=\'%s\'' % (request_data['playbook'], request_data.get('extra_vars', {}))
        os.environ['inventory_id'] = str(request_data.get('inventory_id'))
        log_name = request_data.get('log', '{}_{}.log'.format(request_data.get('playbook'), datetime.now().strftime('%H_%M_%S')))
        log_file = open(os.path.join(log_dir, log_name), 'w')
        ansible = subprocess.Popen(cmd, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=ansible_dir)
        ANSIBLE_INSTANCES[uuid]['process_object'] = ansible
        reader = io.TextIOWrapper(ansible.stdout, encoding='utf-8')
        while True:
            data = reader.read(256)
            if not data:
                break
            log_file.write(data)
            yield 'data: %s\n\n' % json.dumps({'success': '1', 'data' : data})
        rc = ansible.poll()
        yield 'data: %s\n\n' % json.dumps({'success' : '1', 'data' : 'return code is {}'.format(rc)})
        del ANSIBLE_INSTANCES[uuid]
        log_file.close()
    ANSIBLE_INSTANCES[uuid] = {'stream' : stream}
    return jsonify({'success' : 1, 'uuid' : uuid})


@app.route('/play', methods=['GET'])
def play():
    schema = {
        "type" : "object",
        "properties" : {
            "uuid" : {"type" : "string", "pattern" : "^.+$"}
        },
        "required" : ["uuid"]
    }
    try:
        jsonschema.validate(schema=schema, instance=request.args.to_dict())
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'invalid input data'})
    uuid = request.args['uuid']
    instance = ANSIBLE_INSTANCES.get(uuid)
    if instance:
        def_stream = ANSIBLE_INSTANCES[uuid]['stream']
        return Response(def_stream(), mimetype='text/event-stream')
    return jsonify({'success' : 0, 'error' : 'play [{}] does not exist'.format(uuid)})


@app.route('/kill', methods=['GET'])
def kill():
    schema = {
        "type" : "object",
        "properties" : {
            "uuid" : {"type" : "string", "pattern" : "^.+$"}
        },
        "required" : ["uuid"]
    }
    try:
        jsonschema.validate(schema=schema, instance=request.args.to_dict())
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'invalid input data'})
    instance = ANSIBLE_INSTANCES.get(request.args['uuid'])
    if instance:
        ansible = instance.get['process_object']
        ansible.kill()
        del ANSIBLE_INSTANCES[request.args['uuid']]
        return jsonify({'success' : 1})
    return jsonify({'success' : 0, 'error' : 'play [{}] does not exist'.format(request.args['uuid'])})


@app.route('/ansible/<directory>', methods=['GET'])
def get_files_from(directory):
    if directory not in ['ssh', 'extra', 'log', 'play', 'file']:
        return jsonify({'success' : 0, 'error' : 'directory {} is invalid'.format(directory)})
    files = []
    for file in os.listdir(os.path.join(ansible_dir, directory)):
        if os.path.isfile(os.path.join(ansible_dir, directory, file)):
            files.append(file)
    return jsonify({'success' : '1', 'files' : files})


@app.route('/ansible/<directory>/<name>', methods=['GET'])
def get_file(directory,name):
    if directory not in ['ssh', 'extra', 'log', 'play', 'file']:
        return jsonify({'success' : 0, 'error' : 'directory {} is invalid'.format(directory)})
    if not os.path.isfile(os.path.join(ansible_dir, directory, name)):
        return jsonify({'success' : 0, 'error' : 'file {} not exists'.format(name)})
    f = os.path.join(ansible_dir, directory, name)
    content = open(f, 'r').read()
    mime = magic.Magic(mime=True)
    return Response(content, mimetype=mime.from_file(f))


@app.route('/ansible/<directory>', methods=['POST'])
def post_file(directory):
    if directory not in ['ssh', 'extra', 'log', 'play', 'file']:
        return jsonify({'success' : 0, 'error' : 'directory {} is invalid'.format(directory)})
    if 'file' not in request.files:
        return jsonify({'success' : 0, 'error' : 'no file was specified'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success' : 0, 'error' : 'no file was specified'})
    if os.path.isfile(os.path.join(ansible_dir, directory, file.filename)):
        return jsonify({'success' : 0, 'error' : 'file {} already exists'.format(file.filename)})
    file.save(os.path.join(ansible_dir, directory, file.filename))
    return jsonify({'success': '1', 'uri' : '/ansible/{}/{}'.format(directory, file.filename)})


@app.route('/ansible/<directory>/<name>', methods=['DELETE'])
def delete_file(directory, name):
    if directory not in ['ssh', 'extra', 'log', 'play', 'file']:
        return jsonify({'success' : 0, 'error' : 'directory {} is invalid'.format(directory)})
    if not os.path.isfile(os.path.join(ansible_dir, directory, name)):
        return jsonify({'success' : 0, 'error' : 'file {} is absent'.format(name)})
    os.remove(os.path.join(ansible_dir, directory, name))
    return jsonify({'success': '1'})


# INVENTORY
@app.route('/inventory', methods=['GET'])
def get_inventories():
    inventories = Inventory.query.all()
    l = []
    if inventories == None:
        inventories = []
    for i in inventories:
        l.append({'id' : i.id, 'name' : i.name})
    return jsonify({'success' : '1', 'inventories' : l})


@app.route('/inventory/<int:id>', methods=['GET'])
def get_inventory(id):
    i = Inventory.query.get(id)
    if i != None:
        return jsonify({'success' : '1', 'inventory' : {'id': i.id, 'name' : i.name}})
    return jsonify({'success' : '0', 'error' : 'inventory not found'})


@app.route('/inventory', methods=['POST'])
def post_inventory():
    request_data = request.get_json(force=True, silent=True)
    if request_data == None:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    schema = {
        "type" : "object",
        "properties" : {
            "name" : {"type" : "string", "pattern" : "^.+$"}
        },
        "required" : ["name"]
    }
    try:
        jsonschema.validate(schema=schema, instance=request_data)
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    i = Inventory(name=request_data['name'])
    # check for unique
    try:
        db.session.add(i)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success' : '0', 'error' : str(e)})
    return jsonify({'success' : '1', 'inventory' : {'id' : i.id, 'name' : i.name}})

@app.route('/inventory/<int:id>', methods=['PUT'])
def update_inventory(id):
    request_data = request.get_json(force=True, silent=True)
    if request_data == None:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    schema = {
        "type" : "object",
        "properties" : {
            "name" : {"type" : "string", "pattern" : "^.+$"}
        },
        "required" : ["name"]
    }
    try:
        jsonschema.validate(schema=schema, instance=request_data)
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    inventory = Inventory.query.get(id)
    if inventory == None:
        return jsonify({'success' : '0', 'msg' : 'inventory not found'})
    inventory.name = request_data['name']
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success' : '0' , 'error' : str(e)})
    return jsonify({'success' : '1', 'inventory' : {'id' : inventory.id, 'name' : inventory.name}})


@app.route('/inventory/<int:id>', methods=['DELETE'])
def delete_inventory(id):
    inventory = Inventory.query.get(id)
    if not inventory:
        return jsonify({'success' : '0', 'msg' : 'inventory not found'})
    try:
        db.session.delete(inventory)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success' : '0', 'msg' : str(e)})
    return jsonify({'success' : 1})


# HOSTS
@app.route('/host', methods=['GET'])
def get_hosts():
    query = {}
    try:
        if request.args.get('query'):
            query = json.loads(request.args.get('query'))
    except Exception as e:
        return jsonify({'success' : '0', 'error' : 'query json is not valid'})
    schema = {
        "type" : "object",
        "properties" : {
            "inventory_id" : {"type" : "number"}
        },
        "required" : ["inventory_id"]
    }
    try:
        jsonschema.validate(schema=schema, instance=query)
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'query json and schema '})
    hosts = Host.query.filter_by(**query).all()
    l = []
    for h in hosts:
        l.append({'id' : h.id, 'name' : h.name, 'inventory_id' : h.inventory_id})
    return jsonify({'success' : '1', 'hosts' : l})


@app.route('/host/<int:id>', methods=['GET'])
def get_host(id):
    h = Host.query.get(id)
    if h != None:
        return jsonify({'success' : '1', 'host' : {'id': h.id, 'name' : h.name, 'inventory_id' : h.inventory_id}})
    return jsonify({'success' : '0', 'msg' : 'host not found'})


@app.route('/host', methods=['POST'])
def post_host():
    request_data = request.get_json(force=True, silent=True)
    if request_data == None:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    schema = {
        "type" : "object",
        "properties" : {
            "name" : {"type" : "string", "pattern" : "^.+$"},
            "inventory_id" : {"type" : "number"}
        },
        "required" : ["name", "inventory_id"]
    }
    try:
        jsonschema.validate(schema=schema, instance=request_data)
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    # TODO try to unpack
    h = Host(name=request_data['name'], inventory_id=request_data['inventory_id'])
    try:
        db.session.add(h)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success' : 0, 'error' : str(e)})
    return jsonify({'success' : '1', 'host' : {'id' : h.id, 'name' : h.name, 'inventory_id' : h.inventory_id}})


@app.route('/host/<int:id>', methods=['PUT'])
def update_host(id):
    request_data = request.get_json(force=True, silent=True)
    if request_data == None:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    schema = {
        "type" : "object",
        "properties" : {
            "name" : {"type" : "string", "pattern" : "^.+$"}
        },
        "required" : ["name"]
    }
    try:
        jsonschema.validate(schema=schema, instance=request_data)
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    host = Host.query.get(id)
    if host == None:
        return jsonify({'success' : '0', 'error' : 'host [{}] not found'.format(id)})
    try:
        host.name = request_data.json['name']
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success' : '0', 'error' : str(e)})
    return jsonify({'success' : '1', 'host' : {'id' : host.id, 'name': host.name, 'inventory_id' : host.inventory_id}})


@app.route('/host/<id>', methods=['DELETE'])
def delete_host(id):
    host = Host.query.get(id)
    if not host:
        return jsonify({'success' : '0', 'error' : 'host not found'})
    try:
        db.session.delete(host)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success' : '0', 'error' : str(e)})
    return jsonify({'success' : 1})


# VARIABLES
@app.route('/var', methods=['GET'])
def get_vars():
    query = {}
    try:
        if request.args.get('query'):
            query = json.loads(request.args.get('query'))
    except Exception as e:
        return jsonify({'success' : '0', 'error' : 'query json is not valid'})
    schema = {
        "type" : "object",
        "properties" : {
            "host_id" : {"type" : "number"}
        },
        "required" : ["host_id"]
    }
    try:
        jsonschema.validate(schema=schema, instance=query)
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'query json and schema '})
    vars = Variable.query.filter_by(**query).all()
    l = []
    for v in vars:
        l.append({'id' : v.id, 'name' : v.name, 'value' : v.value, 'host_id' : v.host_id})
    return jsonify({'success' : '1', 'vars' : l})


@app.route('/var/<int:id>', methods=['GET'])
def get_var(id):
    v = Variable.query.get(id)
    if v != None:
        return jsonify({'success' : '1', 'var' : {'id': v.id, 'name' : v.name, 'value' : v.value, 'host_id' : v.host_id}})
    return jsonify({'success' : '0', 'error' : 'var not found'})


@app.route('/var', methods=['POST'])
def post_var():
    request_data = request.get_json(force=True, silent=True)
    if request_data == None:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    schema = {
        "type" : "object",
        "properties" : {
            "name" : {"type" : "string", "pattern" : "^.+$"},
            "value" : {"type" : "string", "pattern" : "^.+$"},
            "host_id" : {"type" : "number"}
        },
        "required" : ["name", "value", "host_id"]
    }
    try:
        jsonschema.validate(schema=schema, instance=request_data)
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    v = Variable(name=request.json['name'], value=request.json['value'], host_id=request.json['host_id'])
    try:
        db.session.add(v)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success' : 0, 'error' : str(e)})
    return jsonify({'success' : '1', 'var' : {'id' : v.id, 'name' : v.name, 'value' : v.value, 'host_id' : v.host_id}})


@app.route('/var/<int:id>', methods=['PUT'])
def update_var(id):
    request_data = request.get_json(force=True, silent=True)
    if request_data == None:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    schema = {
        "type" : "object",
        "properties" : {
            "name" : {"type" : "string", "pattern" : "^.+$"},
            "value" : {"type" : "string", "pattern" : "^.+$"}
        },
        "required" : ["name", "value"]
    }
    try:
        jsonschema.validate(schema=schema, instance=request_data)
    except Exception as e:
        return jsonify({'success' : 0, 'error' : 'request contains invalid information'})
    var = Variable.query.get(id)
    if var == None:
        return jsonify({'success' : '0', 'error' : 'var not found'})
    try:
        var.name = request.json['name']
        var.value = request.json['value']
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success' : '0', 'error' : str(e)})
    return jsonify({'success' : '1', 'var' : {'id' : var.id, 'name' : var.name, 'value' : var.value, 'host_id' : var.host_id}})


@app.route('/var/<id>', methods=['DELETE'])
def delete_var(id):
    var = Variable.query.get(id)
    if not var:
        return jsonify({'success' : '0', 'error' : 'variable not found'})
    try:
        db.session.delete(var)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success' : '0', 'error' : str(e)})
    return jsonify({'success' : 1})


