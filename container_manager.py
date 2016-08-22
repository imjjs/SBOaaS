import requests
import json
import threading
import datetime
import math
import logging
from  docker import Client
from abc import ABCMeta, abstractmethod


from constants import *
from dto.model import Host
from simulation_tracker import get_queued_container_count

def delete_async(req_url, headers):
	requests.delete(req_url, headers=headers)
		 
class ContainerManager(object):
	__metaclass__ = ABCMeta	
	
	@abstractmethod		
	def refreshHosts(self, host_capacity=None):
		# should be called at the startup or when host configuration changes
		return
	
	@abstractmethod
	def getClusterHosts(self):
		# both cloud providers have their own host list, and are not integrated currently
		return
			
	@abstractmethod
	def getLock(self):
		return
	
	
	# releases a simulation to host pool
	def releaseHost(self, sim_name, host_key):
		
		host_dict = self.getAssignedHosts(sim_name)
		host = host_dict.get(host_key)
		del host_dict[host_key]
		#print self.getAvailableHosts()
		host.avail_capacity = host.cpu_capacity
		self.getAvailableHosts()[host_key] = host
		#print self.getAvailableHosts()
	
	@abstractmethod
	def updateHostStatus(self, sim_name):
		# book-keeping task, need to find proper location for it
		return	
	
	@abstractmethod
	def startContainer(self, image, host_uri, environ_var, command):
		return
	
	@abstractmethod
	def getContainers(self):
		return


class LXCCloudManager(ContainerManager):

	#separate host list for Linux containers and hypervisors
	_avail_hosts = {}
	_assigned_hosts_to_sim = {}
	_host_lock = threading.Lock()

	def __init__(self, manager_ip, manager_port, manager_api_key, container_host_port, overbooking_ratio):
		#url format 'http://129.59.234.204:8000'
		self.api_host_url = 'http://' + manager_ip + ':' + manager_port 
		self.container_host_port = container_host_port
		self.overbooking_ratio = float(overbooking_ratio)
		#api_key_string = 'ApiKey admin:' + manager_api_key
		#self.headers = {'Authorization': api_key_string, 'Content-type': 'application/json'}	
		self.headers = {'X-Service-Key': manager_api_key }	
		self.post_header = {'X-Service-Key': manager_api_key, 'Content-type': 'application/json'}	
		self.logfile = 'running_containers.csv'
		self.cpu_multiplier = int(CONTAINER_CPU_SHARE_MULTIPLIER)
	
		
	def updateHostStatus(self, sim_name):
		hosts = self.getAssignedHosts(sim_name)
		if hosts is None:
			logging.info('No hosts assigned yet')
			return
		
		logging.info('Fetching container list ...')
		for key, value in hosts.iteritems():
			try:
				container_list = value.client.containers()
				running_count = len(container_list)
				logging.info('Number of containers running on host: ' + value.hostname + ', with id: ' + str(value.id) + ' : ' + str(running_count))
				queued_count = get_queued_container_count(sim_name, value.id)
				logging.info('Number of containers queued on host: ' + value.hostname + ', with id: ' + str(value.id) + ' : ' + str(queued_count))
				#print 'container_list: ' + str(container_list)
				value.avail_capacity = value.cpu_capacity - running_count - queued_count
				with open(self.logfile, "a") as csvfile:
    					csvfile.write(str(datetime.datetime.now()) + ',' + value.hostname + ',' + sim_name + ',' + str(queued_count) + ',' + str(running_count) + '\n')
			except Exception, err:
				logging.error('exception while getting container information on host: ' +  value.hostname)
				logging.exception(err)
				# set capacity to 0, will see in next cycle, what to do
				value.avail_capacity = 0
		
	def refreshHosts(self, host_capacity=None):
		logging.info('Refreshing Docker host list ...')
		host_url = self.api_host_url + SHIPYARD_GET_HOST_LIST_REQUEST
		print self.headers
		resp_str = requests.get(host_url, headers=self.headers)
		print resp_str.text
		hosts = json.loads(resp_str.text)
			
		ALL_HOSTS = {}
		for host_object in hosts:
			name = host_object.get('name')
			if name == 'manager':
				continue
			host = Host()
			#host_object = host_inp.get('engine')
			host.hostname = name
			host.type = 'LXC'
			host.id = host_object.get('name')
			host.resource_uri = host_object.get('addr')
			url = host.resource_uri
			host.client = Client(base_url= url,  version='1.18', timeout=10)
			cpu_string = host_object.get('reserved_cpus')
			host.cpu_capacity = int(cpu_string.split('/')[1].strip())
			#host.cpu_capacity = host_object.get('cpus')
			#for now capacity is same cpu capacity
			host.capacity = host.cpu_capacity*self.overbooking_ratio
			# not used
			host.memory_capacity = 0 #host_object.get('memory')
			host.avail_capacity = host.capacity
			host.assigned = False
			host.sims = {}
			#health = host_object.get('health')
			#if health is None:
			host.status = 'NA'
			#else:
			#	host.status = health.get('status')
			ALL_HOSTS[host.hostname] = host
		return ALL_HOSTS

	def getClusterHosts(self):
		return self.refreshHosts()
		
	def getLock(self):
		return LXCCloudManager._host_lock

	def getContainers(self):
		req_url = self.api_host_url + SHIPYARD_GET_CONTAINERS_REQUEST
		logging.debug('request: ' + req_url)
		resp = requests.get(req_url, headers=self.post_header)
		logging.debug('resp status: ' + str(resp.status_code))
		logging.debug('resp : ' + str(resp.text))
		return json.loads(resp.text)

			
	def createContainer(self, image, name, size, client, hostname, environ_var, command, working_dir):
		
		logging.info ("Starting container with image: " + str(image) + ", hostname: " + str(hostname) + ", environ_var: " + str(environ_var) + ", command: " + str(command) )
		cpu_share = size*self.cpu_multiplier
		try:
			container = self.createContainerRequest(image, name, client, hostname, environ_var, command, cpu_share, working_dir)
		except Exception, err:
			logging.info('Image not found: ' + image)
			client.pull(image, insecure_registry=True)
			container = self.createContainerRequest(image, name, client, hostname, environ_var, command, cpu_share, working_dir)
			
		return container.get('Id')
	
	def createContainerRequest(self, image, name, client, hostname, environ_var, command, cpu_share, working_dir):
		if working_dir == None:
			container = client.create_container(image=image, command=command, detach=True,
		                    tty=True, stdin_open=True,
		                		environment=environ_var,cpu_shares=cpu_share, name=name)
		else:
			
			container = client.create_container(image=image, command=command, detach=True,
		                    tty=True, stdin_open=True,
		                		environment=environ_var,cpu_shares=cpu_share, name=name, working_dir=working_dir)
		return container
		
	def startContainer(self, client, c_id):
		return client.start(c_id)

	def destroyContainer(self, id):
			
		req_url = self.api_host_url + SHIPYARD_DELETE_CONTAINER_REQUEST + id
		logging.debug('request: ' + req_url)
		t = threading.Thread(target=delete_async, args=(req_url, self.headers))
		t.start()
		#logging.info(str(resp.status_code))
		#logging.info(str(resp))
		

	def deployContainer(self, image, name, size, host_name, environ, arg ):
		req_url = self.api_host_url + SHIPYARD_POST_CONTAINERS_REQUEST
                data = {
                            "name": image,
                            "container_name": name,
                            "cpus": size,
                            "type" : "service",
                            "labels": [
                                        host_name
                            ],
                            "args": [arg],
                            "environment": {}
                                        #environ
                            ,
                            "restart_policy": {},
                            "bind_ports": [],
                            "links": {}
                        }
                logging.info('request: ' + str(data))
                resp = requests.post(req_url, data=json.dumps(data), headers=self.post_header)
                logging.info('resp: ' + str(resp))
                logging.info('resp: ' + str(resp.status_code))
                logging.info('resp: ' + str(resp.text))
                return resp.text
	
		      
		
class HypervisorCloudManager(ContainerManager):	

	def __init__(self, manager_ip, manager_port):
		#url format 'http://129.59.234.210:80'
		self.api_host_url = 'http://' + manager_ip + ':' + manager_port 

	def refreshHosts(self, host_capacity=None):
	 	raise NotImplementedError(self.api_host_url)
	
	def getClusterHosts(self):
		 raise NotImplementedError(self.api_host_url)
		 
	def getLock(self):
		raise NotImplementedError(self.api_host_url)
		
	def updateHostStatus(self, sim_name):
		raise NotImplementedError(sim_name)
	
	def getContainers(self):
		raise NotImplementedError()
		
def create_container_manager(manager_type, manager_ip, manager_port, manager_api_key=None, container_host_port=None, overbooking_ratio=None):
		if manager_type == LINUX_CONTAINER_CLOUD_MANAGER:
			return LXCCloudManager(manager_ip, manager_port, manager_api_key, container_host_port, overbooking_ratio)
		elif manager_type == HYPERVISOR_CLOUD_MANAGER:
			return HypervisorCloudManager(manager_ip, manager_port)
		else:
			raise NotImplementedError("Cloud manager has not been implemented...")
