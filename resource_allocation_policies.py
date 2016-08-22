import datetime
import math
import logging
import copy
import Queue

from abc import ABCMeta, abstractmethod

from vsvbp.container import *

from bin_packing import *
from simulation_tracker import get_avg_exec_time
#from dddas_exception import DeadlineMissedException
from constants import *    

from dto.model import SimulationSlot

class Scheduler(object):
	__metaclass__ = ABCMeta	
	
	@abstractmethod		
	def determineResources(self, resource_allocation_input, container_slots):
		# returns the number of units needed
		return
		
class DeadlineBasedScheduler(Scheduler):
	
	def __init__(self):
		self.logfile = 'resources.csv'
	
	def determineResources(self, resource_allocation_input, container_slots):
		logging.info('determining container slots needed for deadline based scheduler ...')
		sim_name = resource_allocation_input.sim_name
		deadline = resource_allocation_input.deadline
		margin = resource_allocation_input.margin
		margin_value = resource_allocation_input.margin_value
		if (deadline < datetime.datetime.now()):
			raise DeadlineMissedException('Deadline already crossed')
		timediff = deadline - datetime.datetime.now()
		# may need margin
		remaining_time = timediff.seconds*1000 + timediff.microseconds/1000 
		logging.info('remaining_time: ' + str(remaining_time))
		#logging.debug('resource_allocation_input.tasks: ' + str(resource_allocation_input))
		output = self.packBestFitDecreasing(sim_name, resource_allocation_input.tasks, container_slots, remaining_time, margin, margin_value)
		logging.debug('packing result: ' + str(output))
		
		if output is None:
			raise DeadlineMissedException('Cannot be finished in remaining time')
		
		new_bin_schedule = output[0]
		old_bin_schedule = output[1]
		to_delete_schedule = output[2]
		logging.info('Extra slots needed: ' + str(len(new_bin_schedule)))
		logging.info(str(output[0]))
		logging.info(str(output[1]))
		logging.info(str(output[2]))
		#for obj in schedule:
		#	logging.info(str(obj))

		return (new_bin_schedule, old_bin_schedule, to_delete_schedule)

		
	def packBestFitDecreasing(self, name, tasks, container_slots, remaining_time, margin, margin_value):
		items = []
		#logging.debug(str(tasks))
		for task_id, task in tasks.iteritems():
				items.append(Item(task_id, [task.exec_time*(1+margin)]))
		logging.info('to pack ' + str(items))
		bins = []
		upper_bound = len(items)
		current_time = datetime.datetime.now()
		for container_slot in container_slots:
			sim_remaining_time  = 0.0
		
			if (hasattr(container_slot, 'active_task')):
				active = container_slot.active_task
				if (active is not None) and (hasattr(active, 'start_time')):
					timediff = current_time - active.start_time 
					elapsed =  timediff.seconds*1000 + timediff.microseconds/1000
					sim_remaining_time = active.exec_time*(1+margin) - elapsed
					container_slot.remaining_capacity = remaining_time - sim_remaining_time
			if not hasattr(container_slot, 'remaining_capacity'):
				container_slot.remaining_capacity = remaining_time
			bins.append(Bin(container_slot.name, container_slot.host, [container_slot.remaining_capacity]))
		
		initial_size = len(bins)
		extra_bins = []

			
		for i in range(0,upper_bound):
			extra_bins.append(Bin("new", None, [remaining_time]))
			
		output = best_fit_decreasing(items, bins, extra_bins)
		if output is None:
			return None
		
		
		new_bin_schedule = []
		logging.info('packed new bins' + str(output[0]))
		logging.info('packed old bins' + str(output[1]))

		new_bins = output[0]
		for bin in new_bins:
				container_slot = SimulationSlot()
				container_slot.name = bin.id
				container_slot.tasks = [] #Queue.Queue()
				for item in bin.items:
					task = tasks.get(item.id)
					container_slot.tasks.append(task) #.put(task) 
				container_slot.remaining_capacity = bin.capacities[0]
				new_bin_schedule.append(container_slot)
		
		old_bin_schedule = []
		to_delete_schedule = []
		old_bins = output[1]

		for assigned_container_slot in container_slots:
			found_bin = None
			for bin in old_bins:
				if ((assigned_container_slot.name == bin.id) and (assigned_container_slot.host == bin.host)):
					found_bin = bin

			# make a copy, dont change the original
			container_slot = copy.copy(assigned_container_slot)
			container_slot.tasks = [] #Queue.Queue()
			if found_bin is None:
				to_delete_schedule.append(container_slot)
			else:
				old_bin_schedule.append(container_slot)
				for item in found_bin.items:
					task = tasks.get(item.id)
					container_slot.tasks.append(task) #.put(task)				
				
			
		return (new_bin_schedule, old_bin_schedule, to_delete_schedule)

class MaxUtilizationScheduler(Scheduler):

	def determineResources(self, resource_allocation_input, container_slots):
		logging.info('determining container slots needed for max utilization scheduler ...')
                sim_name = resource_allocation_input.sim_name
                old_bin_schedule = None
                to_delete_schedule = None
		new_bin_schedule = []
	 	#container_slot = SimulationSlot()
		#new_bin_schedule.append(container_slot)
                return (new_bin_schedule, old_bin_schedule, to_delete_schedule)		

class ResourceBasedScheduler(Scheduler):

	def determineResources(self, resource_allocation_input, container_slots):
		raise NotImplementedError('Not supported yet')	
		


def create_scheduler(policy_name):
		if policy_name == 'DEADLINE':
			return DeadlineBasedScheduler()
		elif policy_name == 'RESOURCE':
			return ResourceBasedScheduler()
		elif policy_name == 'SATURATION':
			return MaxUtilizationScheduler()
		elif policy_name == 'COMBINED':
			raise NotImplementedError('Not supported yet')			
		else:
			raise NotImplementedError("Not supported")
