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

def activate_task(sim_manager, container_manager, host, sim_name, sim_slot, finish_task_id=None):
		logging.info('Activating a task from ' + host.hostname + ' ' + sim_slot.name)
		current_time = datetime.datetime.now()
		if finish_task_id is not None:
			sim_manager.logSimTaskEnd(sim_name, finish_task_id, current_time)

		if  (not hasattr(sim_slot, 'active_task')) or (sim_slot.active_task is None):
				if (sim_slot.tasks is None) or (not sim_slot.tasks):
					logging.warn('No task schedule found for ' + sim_slot.name + ' , last task ' + str(finish_task_id ))
					return
				sim_slot.active_task = sim_slot.tasks.pop(0)
				task_id = sim_slot.active_task.id
				logging.info('Activating task : ' + sim_name + ' : ' +  str(sim_slot.active_task.id))
				status = sim_manager.activateTask(sim_name, sim_slot.active_task.id, host.hostname, current_time)
				if not status:
					logging.warn( sim_name + ' : ' +  str(sim_slot.active_task.id) + 'already scheduled on host ' \
						 + sim_slot.active_task.hostname \
						+ ' cannot do again for slot ' + str(sim_slot.name))		
					sim_slot.active_task = None
					return
							
				sim = sim_manager.getSimulation(sim_name)
				# update the remaining capacity for the slot
				#timediff = sim.getDeadline() - datetime.datetime.now()
			        # may need margin
			        #remaining_time = timediff.seconds*1000 + timediff.microseconds/1000
				#sim_slot.remaining_capacity = remaining_time -  sim_slot.active_task.exec_time
				container_name =  sim_name + CONTAINER_NAME_SPLITTER +  str(task_id)
				try:
					
					container_id = container_manager \
						.createContainer(sim.image, container_name, \
								 sim.resource_size, \
								host.client, host.hostname, sim_slot.active_task.sim_environ, sim.command, sim.working_dir)
					output = container_manager.startContainer(host.client, container_name)
					sim_manager.markRunningTask(sim_name, task_id)
						
					logging.info('Started container for simulation: ' + sim_name + ', task id: ' + str(task_id))
				except Exception, e:
					logging.warn (e)
					
					try: 
						container_manager.startContainer(host.client, container_name)
						sim_manager.markRunningTask(sim_name, task_id)
					except Exception, ex:
						logging.exception(ex)
					# got exception move the task back in the queue
					if sim_slot.active_task is not None:
						sim_slot.active_task.status = SIMULATION_STATE_SCHEDULED
						sim_slot.active_task = None
					 

# remove the thread based apporach, not working
class HostDeploymentService(object):
	def __init__(self, host, container_manager, sim_manager):
	
		#initialize
		logging.info(' Initializing deployment service')
		self.host = host
		self.running = True
		self.sim_resources = {}
		self.sim_manager = sim_manager
		self.container_manager = container_manager
		#self.task_queue = Queue.Queue()
		self.sim_res_lock = RWLock()

	def createSlot(self, rem_capacity):
                sim_slot = SimulationSlot()
                sim_slot.host = self.host.hostname
                sim_slot.active_task = None
                sim_slot.tasks = None
                sim_slot.remaining_capacity = rem_capacity
                sim_slot.name = ''.join(random.choice(string.ascii_uppercase) for i in range(12))
		sim_slot.condition_obj = RWLock()
                return sim_slot

		
	def addSlot(self, sim_name, slot):
		sim_res = self.sim_resources.get(sim_name)
		logging.info('add: ' + slot.name + ' on '  + slot.host)
		if sim_res is None:
			sim_res = SimulationResource()
			sim_res.slots = {}
			self.sim_resources[sim_name] = sim_res
		sim_res.slots[slot.name] = slot	
	
	def hasSimResource(self, sim_name):
		return  (self.sim_resources.get(sim_name) is not None)

	def getSimSlots(self, sim_name):
		res =  self.sim_resources.get(sim_name)
		if res is None:
			return None
		slots = []
		for slot_name, slot in res.slots.iteritems():
			slots.append(slot)
		return slots
		
	def addSchedule(self, sim_name, container_slot_schedule):
		logging.debug('adding schedule: ' + str(container_slot_schedule))
		# should replace the old schedule
		sim_res = self.sim_resources.get(sim_name)
		#self.sim_res_lock.writer_acquire()
		for sched_slot in container_slot_schedule:
			logging.info('queueing: ' + sim_name + ' ' + sched_slot.name)
			logging.info(str(sched_slot))
			slot = sim_res.slots.get(sched_slot.name)
			try:
				slot.condition_obj.writer_acquire() 
				slot.tasks = sched_slot.tasks
				slot.remaining_capacity = sched_slot.remaining_capacity
				thread.start_new_thread( activate_task, (self.sim_manager, self.container_manager, self.host, sim_name, slot,))
			finally:
				slot.condition_obj.writer_release() 
		
		
	def scheduleNext(self, sim_name, finished_task_id):

		sim_res = self.sim_resources.get(sim_name)
		if sim_res is None:
			logging.error('Simulation ' + sim_name + ' has already finished')
			return
		# will check if needs to be changed
		for slot_name, slot in sim_res.slots.items():
			try:
				slot.condition_obj.reader_acquire() 
				# Should lock the slot as we are making a task as we are removing the active task
				if slot.active_task is not None and  slot.active_task.id == finished_task_id:
					slot.active_task = None
	
					logging.info('queueing: ' + sim_name + ' ' + slot_name)
					activate_task(self.sim_manager, self.container_manager, self.host, sim_name, slot, finished_task_id)
					return
			finally:
				slot.condition_obj.reader_release() 
		# not found, just log it
		self.sim_manager.logSimTaskEnd(sim_name, finished_task_id, datetime.datetime.now())
		
					
	def freeAllContainerSlots(self, sim_name):
		try:
			self.sim_res_lock.writer_acquire()
			sim_res = self.sim_resources.get(sim_name)
			if sim_res is None:
				return 0
			freed_containers = len(sim_res.slots)
			del self.sim_resources[sim_name]
			return freed_containers
		finally:
			self.sim_res_lock.writer_release()

	def freeContainerSlot(self, sim_name, slot):
		logging.info('remove: ' + slot.name + ' on '  + slot.host)
		try:
			self.sim_res_lock.writer_acquire()
			sim_res = self.sim_resources.get(sim_name)
			if sim_res is None:
				return 0
			del sim_res.slots[slot.name]
			return 1
		finally:
			self.sim_res_lock.writer_release()
			
			
	def stop(self):
		self.running = False

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
	'''
	def updateClusterCapacity(self):
		for host in self._ASSIGNED_HOSTS:
			self.container_manager.updateHostStatus()
	'''
		
	def deployContainer(sim_name, number_of_containers):
		# container number can be negative, release the resource in that case
		# figure out if it crossed the threshold to change
		return
	
	def checkAvailableCapacity(self, sim_resource_size, count):
		# keep some margin
		to_assign = int(count * 1.3)
		logging.info('check if host has capacity for size: ' + str(sim_resource_size) + ', count: ' + str(count))
		#change the logic to check all the hosts
		for  hostname, host in self._CLUSTER_HOSTS.iteritems():	
			logging.debug(str(host))	
			container_per_host = (host.capacity / sim_resource_size)
			logging.info('container capacity per host: ' + str(container_per_host))
			if host.assigned == False:
				to_assign = to_assign - container_per_host 
			if to_assign < 1:
				logging.info('capacity available')
				return True
			
		logging.warn('capacity not available')
		return False

	def getTotalCapacity(self, sim_resource_size):
                logging.info('get host  capacity for size: ' + str(sim_resource_size) )
                #change the logic to check all the hosts
		capacity = 0
                for  hostname, host in self._CLUSTER_HOSTS.iteritems():
                        logging.debug(str(host))
                        container_per_host = (host.capacity / sim_resource_size)
                        logging.info('container capacity for  host: ' + str(hostname)+ ' is ' + str(container_per_host))
                        if host.assigned == False:
				capacity += container_per_host

                return capacity



	def createSlot(self, hostname, rem_capacity):
		sim_slot = SimulationSlot()
		sim_slot.host = hostname
		sim_slot.active_task = None
		sim_slot.tasks = None
		sim_slot.remaining_capacity = rem_capacity
		sim_slot.name = ''.join(random.choice(string.ascii_uppercase) for i in range(12))
		return sim_slot
	
		
	def allocateResources(self, sim_name, size, deadline, count, sim_manager):
		assigned_slots = []
		remaining_count = count
		timediff = deadline - datetime.datetime.now()
                # may need margin
                remaining_time = timediff.seconds*1000 + timediff.microseconds/1000
		
		# prefer the host which has already been allocated
		for hostname in self._assigned_host_ids:
			host = self._CLUSTER_HOSTS.get(hostname)
			if host.deployment_service.hasSimResource(sim_name):
				logging.debug(sim_name + ' present on host: ' + hostname)
				logging.debug('avail capacity: ' + str(host.avail_capacity) + ', size: ' + str(size) )
				while (host.avail_capacity - size) >= 0:
					logging.debug('avail capacity: ' + str(host.avail_capacity) + ', size: ' + str(size) )
					logging.debug('remaining count: ' + str(remaining_count))
					if remaining_count == 0:
						
						return assigned_slots
					host.avail_capacity = host.avail_capacity - size
					sim_slot = host.deployment_service.createSlot(remaining_time)
					host.deployment_service.addSlot(sim_name, sim_slot)
					assigned_slots.append(sim_slot)
					remaining_count = remaining_count - 1
				
		# pack the already assigned resources
		for hostname in self._assigned_host_ids:
			host = self._CLUSTER_HOSTS.get(hostname)
			logging.debug('Will try to allocate: ' + sim_name + '  on previously allocated host: ' + hostname)
			while (host.avail_capacity - size) >= 0:
				logging.debug('remaining count: ' + str(remaining_count))
				if remaining_count == 0:
					return assigned_slots
				
				host.avail_capacity = host.avail_capacity - size
				sim_slot = host.deployment_service.createSlot(remaining_time)
				host.deployment_service.addSlot(sim_name, sim_slot)
				assigned_slots.append(sim_slot)
				remaining_count = remaining_count - 1
				
		if remaining_count == 0:
			return assigned_slots

		# get new resource
		for hostname, host in self._CLUSTER_HOSTS.iteritems():
			host = self._CLUSTER_HOSTS.get(hostname)
			if host.assigned is True:
				continue
			logging.info(sim_name + ' will be assigned on host: ' + hostname)
			self._assigned_host_ids.append(hostname)
			host.assigned = True
			if (not hasattr(host , 'deployment_service')):
				host.deployment_service = HostDeploymentService(host, self.container_manager, sim_manager)
				#host.deployment_service.start()
			first = True
			while (host.avail_capacity - size) >= 0:
				logging.debug('remaining count: ' + str(remaining_count))
				if remaining_count == 0:
					return assigned_slots
				host.avail_capacity = host.avail_capacity - size
				sim_slot = host.deployment_service.createSlot(remaining_time)
				host.deployment_service.addSlot(sim_name, sim_slot)
				assigned_slots.append(sim_slot)
				remaining_count = remaining_count - 1
				if remaining_count == 0:
					return assigned_slots

		logging.error('Could not allocate slot, ran out of resources !!!!')
		raise NoCapacityException('Ran out of resources!')

	def getAssignedContainers(self, sim_name):
		container_slots = []
		for hostname in self._assigned_host_ids:
			host = self._CLUSTER_HOSTS.get(hostname)
			slots = host.deployment_service.getSimSlots(sim_name)
			if slots is not None:
				container_slots = container_slots + slots

		return container_slots
	
	def assignNewSchedule(self, sim_name, size, deadline, new_slot_schedule, old_slot_schedule, toremove_slot_schedule, sim_manager):
		logging.info(' Assigning new schedule for simulation: ' + sim_name)
		new_count = len(new_slot_schedule)
		new_slots = None
		if new_count > 0:
			logging.info('additional resources have to be assigned: ' + str(new_count))
			new_slots = self.allocateResources(sim_name, size, deadline, new_count, sim_manager)
		logging.info('assigning schedule for each slot')
		logging.debug('new schedule: ' + str(new_slot_schedule))

		for sched_slot in new_slot_schedule:
				slot = new_slots.pop(0)
				slot.tasks = sched_slot.tasks
				old_slot_schedule.append(slot)

		schedule_per_host = {}
		
		sum_resources = 0

		for sched_slot in old_slot_schedule:
			saved_slots = schedule_per_host.get(sched_slot.host)
			logging.debug('saved slot' + str(saved_slots))
			if saved_slots is None:
				schedule_per_host[sched_slot.host] = [sched_slot]
			else:
				saved_slots.append(sched_slot)
				logging.info('New slot count for host ' + str(sched_slot.host) + ' simulation ' + sim_name + ' is ' + str(len(saved_slots)))
			if sched_slot.active_task is not None:
				task_id = sched_slot.active_task.id
			else:
				task_id = -1
			sum_resources = sum_resources + 1
			sim_manager.logRes(sim_name, sched_slot.name, sched_slot.host, task_id, len(sched_slot.tasks))
		
		sim_manager.logtotal(sim_name, sum_resources)
					
		# we have created a schedule per host
		logging.debug('logging schedule per host: ' + str(schedule_per_host))
			
		#iterate over view
		for hostname, sched in schedule_per_host.items():
			host = self._CLUSTER_HOSTS.get(hostname)
			sim_manager.logHostRes(sim_name, hostname, len(sched))
			if sched is None:
				logging.warn("No schedule found for host: " + hostname)
			else:
				#host.deployment_service.addSchedule(sim_name, schedule_per_host.get(hostname))
				host.deployment_service.addSchedule(sim_name, sched)


		# threshold of 5, change it later to be dynamic
		if len(toremove_slot_schedule) > 1:

			for sched_slot in toremove_slot_schedule:
				logging.info('releasing container slot: ' + sched_slot.name)
				sim_manager.logRes(sim_name, sched_slot.name, sched_slot.host, task_id, len(sched_slot.tasks))
				self.releaseSlot(sim_name, sched_slot, size)

		sim_manager.logFlush(sim_name)

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

	def scheduleNextSimTask(self, hostname, sim_name, finished_task_id):
		host = self._CLUSTER_HOSTS.get(hostname)
		if host.deployment_service is None:
			logging.error('Host ' + hostname + ' is not allocated, cannot schedule a task!!!!')
		else:
			host.deployment_service.scheduleNext(sim_name, finished_task_id)
	
	def freeSimulation(self, sim_name, size):
		hostnames = copy.copy(self._assigned_host_ids)
		for hostname in hostnames:
			host = self._CLUSTER_HOSTS.get(hostname)
			logging.info('Free up resource on host: ' + hostname +  '  if the simulation exists ')
			freed_container_count = host.deployment_service.freeAllContainerSlots(sim_name)
			self._returnCapacity(host, size, freed_container_count)
			
	def releaseSlot(self, sim_name, slot, size):
			host = self._CLUSTER_HOSTS.get(slot.host)
			logging.info('Free up slot on host: ' + host.hostname )
			freed_container_count = host.deployment_service.freeContainerSlot(sim_name, slot)
			self._returnCapacity(host, size, freed_container_count)

	def _returnCapacity(self, host, size, count):
                        host.avail_capacity = host.avail_capacity + size*count
                        if host.capacity == host.avail_capacity:
                                logging.info('Releasing host ' + host.hostname + ' !!!!')
                                self._assigned_host_ids.remove(host.hostname)
                                host.assigned = False
                                #host.deployment_service.stop()
                                #host.deployment_service = None

