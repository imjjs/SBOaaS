import logging
import thread
import ConfigParser
import os

from container_manager import create_container_manager
from resource_manager_simple import ResourceManager
from resource_allocation_policies import create_scheduler
from simulation_manager import *

from constants import *

def finish_sim_task(manager, sim_name, sim_id, duration, result):
	logging.info('logging sim response ' )
	manager.finishAndScheduleSimTask(sim_name, int(sim_id), duration, result)

# class 
class DDDASManager(object):

	def __init__(self, conf_file):
		self.initialize(conf_file)				
 
	def initialize(self, conf_file):
		logging.info('Initializing System Manager ...')		
		system_conf = ConfigParser.ConfigParser()
		system_conf.read(conf_file)
		self.resource_manager = ResourceManager(self.createContainerManager(system_conf))
		# initialize the host list, can be updated on demand
		logging.info('Refreshing the host list: '  + ' ...')
		self.resource_manager.initializeCluster()
		self.policy = self.createScheduler(system_conf)
		valid_sims = system_conf.get('SIMULATION_DETAILS', 'VALID_SIMS')
		sim_service_freq = float(system_conf.get('SCHEDULING_DETAILS', 'SIM_SCHEDULER_FREQUENCY'))
		sim_status_update_freq = float(system_conf.get('SCHEDULING_DETAILS', 'SIM_STATUS_UPDATE_FREQUENCY'))
		self.simulation_manager = SimulationManager(valid_sims, self.policy, sim_service_freq, sim_status_update_freq, self.resource_manager)
	    	
	
	def refreshHostList(self):
		self.container_manager.refreshHosts()
		logging.info('Host list refreshed...')
	
	def createScheduler(self, system_conf):		
		policy_val = system_conf.get('SCHEDULING_DETAILS', 'ALLOCATION_POLICY')
		return create_scheduler(policy_val)
	
	def createContainerManager(self, host_conf):		
		manager_type = host_conf.get('CLOUD_DETAILS', 'CLOUD_MANAGER')
		ip = host_conf.get('SERVERS', 'CLOUD_MANAGER_IP')
		port = host_conf.get('SERVERS', 'CLOUD_MANAGER_PORT')
		api_key = host_conf.get('SERVERS', 'CLOUD_MANAGER_API_KEY')
		overbooking = host_conf.get('SERVERS', 'CLOUD_HOST_CPU_OVERBOOKING') 
		
		# only needed for Linux container host
		container_host_port = host_conf.get('SERVERS', 'CONTAINER_HOST_PORT') 
		
		logging.info('Creating Container Manager of type: ' + manager_type + ' ...')
		return create_container_manager(manager_type, ip, port, manager_api_key=api_key, 
				container_host_port=container_host_port, overbooking_ratio=overbooking)
			
			
	def admissionControl(self, sim_type, sim_config_file, cpu=None, sim_count=None, deadline=None):
		try:
			if (cpu is None):
				sim_conf_file_path = os.path.join(os.path.dirname(__file__), SIMULATION_CONF_DIR + sim_config_file)
				sim_conf = ConfigParser.ConfigParser();
				sim_conf.read(sim_conf_file_path);
				cpu = sim_conf.get('PROCESS_DETAILS', 'CPU_COUNT')
				sim_count = sim_conf.get('PROCESS_DETAILS', 'NUMBER_OF_SIMS')
				deadline = sim_conf.get('SIM_INPUT', 'DEADLINE')
			capacity_available = self.resource_manager.getTotalCapacity(int(cpu))
			sim = self.simulation_manager.createSimulation(sim_type, sim_config_file, int(cpu), int(capacity_available), float(deadline))
			self.simulation_manager.startSimulation(sim.getName(), capacity_available )
			return sim.getName()
				
		except Exception, err:
			logging.error("problem while performing admission control")
			logging.exception(err)
			return ADMN_CNTRL_INCORRECT_CONFIG

	def logSimEnd (self, sim_name, sim_id, duration, result):
		thread.start_new_thread( finish_sim_task, (self.simulation_manager, sim_name, sim_id, duration, result))
		return "LOGGED" 
	
	def dumpResult (self, sim_name, file_name):
		sim = self.simulation_manager.getSimulation(sim_name)
		if sim is None:
			return "not_found"
		write_result(sim, file_name)
		return "DUMPED" 
