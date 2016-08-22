import cherrypy
import logging
import ConfigParser
import os.path

import requests
sess = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=500, pool_maxsize=500)
sess.mount('http://', adapter)

from dddas_manager import DDDASManager
#from simulation_tracker import log_sim_end, log_sim_result, dump_result
from constants import *

class Root(object):

	def __init__(self):
		logging.info('Initializing simulation service ...')
		system_conf_file = os.path.join(os.path.dirname(__file__), CLOUD_SIM_FILE)		
		self.dddas_manager = DDDASManager(system_conf_file)
		
	@cherrypy.expose
	def index(self):
		return "Hello World!"
	
	@cherrypy.expose
	def runSimulation(self, sim_type, sim_file):
		return self.dddas_manager.admissionControl(sim_type, sim_file)


	@cherrypy.expose
	def run_sims(self, sim_type, sim_file, cpu, sim_count, deadline):
		return self.dddas_manager.admissionControl(sim_type, sim_file, cpu, sim_count, deadline)
		
	@cherrypy.expose
	def logSimulationDetails(self, sim_name, sim_id, duration, result):
		return self.dddas_manager.logSimEnd(sim_name, sim_id, duration, result)
		
	@cherrypy.expose
	def dumpResult(self, sim_name, file_name):
		return self.dddas_manager.dumpResult(sim_name, file_name)
	
		
	@cherrypy.expose
	def logSimulationResult(self, sim_name, p1, p2, p3, p4, p5, c1, c2, c3, c4, c5):
		
		return log_sim_result(sim_name, p1, p2, p3, p4, p5, c1, c2, c3, c4, c5)

if __name__ == '__main__':

	logging.basicConfig(format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s -line %(lineno)d - thread %(thread)d - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='./dddas.log', level=logging.INFO)
	logging.info('#############################################################################');	
	logging.getLogger('cherrypy.access').propagate = False
	host_conf_file = os.path.join(os.path.dirname(__file__), CLOUD_SIM_FILE)
	host_conf = ConfigParser.ConfigParser();
	host_conf.read(host_conf_file);
	port = int(host_conf.get('HOST', 'PORT'))
	cherrypy.config.update({'server.socket_host': '0.0.0.0',
							 'server.socket_port': port,
							}) 
	cherrypy.quickstart(Root())
