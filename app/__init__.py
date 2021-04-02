from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from configparser import ConfigParser
import os

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# mysql config
config = ConfigParser()
config.read('config.ini')
host = config.get('mysql', 'host')
database = config.get('mysql', 'database')
user = config.get('mysql', 'user')
password = config.get('mysql', 'password')
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}/{}'.format(user, password, host, database)
db = SQLAlchemy(app)

# ansible dirs
ansible_dir = 'ansible'
extra_dir = os.path.join(ansible_dir, 'extra')
prepare_dir = os.path.join(ansible_dir, 'prepare')
log_dir = os.path.join(ansible_dir, 'log')
play_dir = os.path.join(ansible_dir, 'play')
ssh_dir = os.path.join(ansible_dir, 'ssh')
file_dir = os.path.join(ansible_dir, 'file')

from app import controllers
