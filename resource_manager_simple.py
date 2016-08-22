import requests
import json
from  threading import Thread, Lock #,Condition
import datetime, time
import math, string, random
import logging
import thread
import Queue
import copy
from rwlock import RWLock

from abc import ABCMeta, abstractmethod


from constants import *
from dddas_exception import NoCapacityException
from dto.model import Host, SimulationSlot, SimulationResource, SimulationTaskContainer
from simulation_tracker import get_queued_container_count

def activate_task(sim_manager, container_manager, host, sim, task, finish_task_id=None):
		sim_name = sim.getName()
		logging.info('Activating task for ' + host.hostname + ' task: ' + str(task.id))
		current_time = datetime.datetime.now()
		if finish_task_id is not None:
			sim_manager.logSimTaskEnd(sim_name, finish_task_id, current_time)

		logging.info('Activating task : ' + sim_name + ' : ' +  str(task.id))
		status = sim_manager.activateTask(sim_name, task.id, host.hostname, current_time)
		container_name =  sim_name + CONTAINER_NAME_SPLITTER +  str(task.id)
		try:
				
			container_id = container_manager \
				.createContainer(sim.image, container_name, \
						 sim.resource_size, \
						host.client, host.hostname, task.sim_environ, sim.command, sim.working_dir)
			logging.info('created container with id: ' + container_id)
			output = container_manager.startContainer(host.client, container_name)
			sim_manager.markRunningTask(sim_name, task.id)
					
			logging.info('Started container for simulation: ' + sim_name + ', task id: ' + str(task.id))
		except Exception, e:
			logging.warn (e)
			
			try: 
				container_manager.startContainer(host.client, container_name)
				sim_manager.markRunningTask(sim_name, task.id)
			except Exception, ex:
				logging.exception(ex)
			# got exception move the task back in the queue
		task.status = SIMULATION_STATE_SCHEDULED

class ResourceManager(object):
	
	def __init__(self, container_manager):
		#self._ASSIGNED_HOSTS = []
		#self._CLUSTER_HOSTS = []
		self._AVAIL_CONTAINER_CPUS = 0
		self._AVAIL_CONTAINER_MEMORY = 0
		self.container_manager = container_manager
		

	def initializeCluster(self):
		self._CLUSTER_HOSTS = self.container_manager.getClusterHosts()
		self._assigned_host_ids = []
		logging.info('The available hosts are: ' + str(self._CLUSTER_HOSTS))
	

	def getTotalCapacity(self, sim_resource_size):
                logging.info('get host  capacity for size: ' + str(sim_resource_size) )
                #change the logic to check all the hosts
		capacity = 0
                for  hostname, host in self._CLUSTER_HOSTS.iteritems():
                        container_per_host = (host.capacity / sim_resource_size)
                        logging.info('container capacity for  host: ' + str(hostname)+ ' is ' + str(container_per_host))
                        if host.assigned == False:
				capacity += container_per_host

                return capacity

	def scheduleSimulationAllPendingTasks(self, sim, sim_manager):
		# prefer the host which has already been allocated
		tasks = sim.getTasks()
			
		index = sim.first_pending_id
		tasks_len = sim.id - index + 1
		logging.info("remaining tasks: " + str(tasks_len))

		for  hostname, host in self._CLUSTER_HOSTS.iteritems():
			# reset host for now
			host.avail_capacity = host.capacity
			if index - sim.first_pending_id + 1 >= tasks_len:
				break	
			host.assigned = True
			size = sim.getResourceSize()
			remain_capacity = host.avail_capacity
			#logging.info('avail capacity: ' + str(host.avail_capacity) + ', size: ' + str(size) )
			while remain_capacity > 0:
				remain_capacity =  (host.avail_capacity - size)
				host.avail_capacity = remain_capacity
				task = tasks.get(index)
				logging.info('activating task: ' + str(index) + ' on host ' +  hostname)
				thread.start_new_thread( activate_task, (sim_manager, self.container_manager, host, sim, task))
				index += 1

	def scheduleNextSimTask(self, sim_manager, hostname, sim, finished_task_id, new_task):
		host = self._CLUSTER_HOSTS.get(hostname)
		thread.start_new_thread( activate_task, (sim_manager, self.container_manager, host, sim, new_task, finished_task_id))

	def getRecentlyFinishedSimulations(self):
		containers = self.container_manager.getContainers()
		finished_containers = []
		for container in containers:
			logging.debug('name : ' + container.get('name'))
			if container.get('state') != CONTAINER_STATE_STOPPED:
				continue
			name_parts = container.get('name').split('/')
			if name_parts == 1:
				continue
			name_parts = name_parts[1].split(CONTAINER_NAME_SPLITTER)
			simulation_name = name_parts[0]
			if len(name_parts) > 1:
				task_id = name_parts[1]
				task = SimulationTaskContainer()
				task.sim_name = simulation_name
				task.id = int(task_id)
				task.sim_id = container.get('id')
				task.hostname = container.get('engine').get('labels')[0]
				finished_containers.append(task)
		logging.debug('finished containers: ' + str(finished_containers))
		return finished_containers

	def cleanUpSimTask(self, id):
		logging.info('Destroy container: ' + id)
		self.container_manager.destroyContainer(id)


