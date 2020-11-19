class AnsibleHost(object):

	def __init__(self, host_name, ansible_host, ansible_user, ansible_password):
		self.host_name = host_name
		self.ansible_host = ansible_host
		self.ansible_user = ansible_user
		self.ansible_password = ansible_password
