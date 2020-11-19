import yaml
from ansible_host import AnsibleHost

class Inventory(object):

	def __init__(self, inventory_file):
		self.inventory_file = inventory_file

	def get_host(host_name):
		pass

	def add_host(ansible_host):
		pass

class StupidInventory(Inventory):

	def __init__(self, inventory_file):
		Inventory.__init__(self, inventory_file)		

	def get_host(self, host_name):
		host = None
		with open(self.inventory_file, 'r') as file:
			data = yaml.load(file, Loader=yaml.FullLoader)
			# awful working style with dicts in my opinion... This code is a piece of shit
			host = data["all"]["hosts"][host_name]
			host = AnsibleHost(host_name, host["ansible_host"], host["ansible_user"], host["ansible_password"])
		return host

	def add_host(self, ansible_host):
		with open(self.inventory_file, 'r+') as file:
			data = yaml.load(file, Loader=yaml.FullLoader)
			if ansible_host.host_name in data["all"]["hosts"]:
				print("host already exists")
				return
			data["all"]["hosts"][ansible_host.host_name] = ansible_host.__dict__
			yaml.dump(data, file)
		print ("hosts added!")
			
