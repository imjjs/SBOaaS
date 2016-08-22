import datetime
import logging

from dto.model import SimulationsModel, SimulationInstanceModel

# global var to track all the simulations	
__sim_tracker_object = {}

def add_simulation(sim_name, total_count, est_exec_err):
	simulation = SimulationsModel()
	simulation._total_count = total_count
	simulation._avg_exec_err = est_exec_err
	simulation._start_time = datetime.datetime.now()
	simulation._end_time = None
	simulation._all_sim_performed_time = None
	simulation._simulations = {}
	simulation._last_container_count = 0
	simulation._finished = False
	__sim_tracker_object[sim_name] = simulation
	
def log_sim_start(sim_name, sim_id, host_key):
	instance = SimulationInstanceModel()
	instance._sim_id = sim_id
	instance._start_time = datetime.datetime.now()
	instance._schedule_time = None
	instance._end_time = None
	instance._running_on_host = host_key
	__sim_tracker_object[sim_name]._simulations[(sim_name, sim_id)] = instance
	
def log_sim_scheduled(sim_name, sim_id):	
	__sim_tracker_object[sim_name]._simulations[(sim_name, sim_id)]._schedule_time = datetime.datetime.now()
	
def log_sim_end(sim_name, sim_id, duration):
	logging.info('Received: sim_name: ' + sim_name + ', sim_id: ' + sim_id + ', duration: ' + duration )
	simulation = __sim_tracker_object.get(sim_name)
	if simulation is None:
		return 'not from current sim'
	sim_instance = simulation._simulations[(sim_name, int(sim_id))]
	sim_instance._end_time = datetime.datetime.now()
	sim_instance._actual_duration = duration
	timediff = sim_instance._end_time - sim_instance._start_time
	current_exec_duration = timediff.seconds*1000 + timediff.microseconds/1000
	simulation._avg_exec_duration = (simulation._avg_exec_duration*simulation._last_container_count + current_exec_duration) / (simulation._last_container_count + 1.0)
	simulation._last_container_count = simulation._last_container_count + 1
	
	if(simulation._last_container_count == simulation._total_count):
		simulation._all_sim_performed_time = datetime.datetime.now()
	return 'success'
	
def log_sim_result(sim_name,  p1, p2, p3, p4, p5, c1, c2, c3, c4, c5):
	result_line = sim_name + ' results: ' + '(' + p1 + ',' + c1 + '),' + ' (' + p2 + ',' + c2 + '),' + ' (' + p3 + ',' + c3 + '),' + ' (' + p4 + ',' + c4 + '),' + ' (' + p5 + ',' + c5 + ')'
	logging.info(result_line)
	simulation = __sim_tracker_object[sim_name]
	simulation._end_time = datetime.datetime.now()
	# commenting for now
	#simulation._finished = True
	
	logging.info('--------------------Result-------------------')
	logging.info(str(simulation))
	write_result(simulation, "simulation_result.txt", result_line)
	return 'success'
	
def dump_result(file_name):
	simulation = __sim_tracker_object.itervalues().next()
	file_path = '/opt/dddas_manager/' + file_name
	write_result(simulation, file_path)
	return file_path
	
def write_result(simulation, file_name, extra=None):
	fo = open(file_name, "wb")
	if(extra is not None):
		fo.write( extra + '\n')
	fo.write( '_total to run : ' +  str(simulation._total_count) + '\n' )
	fo.write( '_avg_exec_duration: ' +  str(simulation._avg_exec_duration) + '\n' )
	fo.write( '_start_time: ' +  str(simulation._start_time) + '\n' )
	fo.write( '_end_time: ' +  str(simulation._end_time) + '\n' )
	fo.write( '_current_time: ' +  str(datetime.datetime.now()) + '\n' )
	if simulation._all_sim_performed_time is not None:
		fo.write( '_all_sim_performed_time: ' +  str(simulation._all_sim_performed_time) + '\n' )
	fo.write( '_last_container_count: ' +  str(simulation._last_container_count) + '\n' )
	fo.write( '_total_container_count: ' +  str(len(simulation._simulations)) + '\n' )
	fo.write( '_finished: ' +  str(simulation._finished) + '\n' )
	for key, instance in simulation._simulations.iteritems():
		fo.write( '_sim_id: ' +  str(instance._sim_id) + ', ' )
		fo.write( '_start_time: ' +  str(instance._start_time) + ', ' )
			
		fo.write( ' _running_on_host: ' +  str(instance._running_on_host) + ', ' )
		if instance._schedule_time is not None:
					fo.write( ' _schedule_time: ' +  str(instance._schedule_time) + ', ' )					
		
		if instance._end_time is not None:
			fo.write( ' _end_time: ' +  str(instance._end_time) + ', ' )
			fo.write( ' _actual_duration: ' +  str(instance._actual_duration) + ', '  )
			timediff = instance._end_time - instance._start_time
			current_exec_duration = timediff.seconds*1000 + timediff.microseconds/1000
			fo.write( ' _total_duration: ' +  str(current_exec_duration) + ', '  )
			if instance._schedule_time is not None:
				timediff = instance._end_time - instance._schedule_time
				current_exec_duration = timediff.seconds*1000 + timediff.microseconds/1000
				fo.write( ' _after_schedule_duration: ' +  str(current_exec_duration)  )
		fo.write( '\n' )	
	# Close opend file
	fo.close()
	
def get_avg_exec_time(sim_name):
	return __sim_tracker_object[sim_name]._avg_exec_duration
	
def get_queued_container_count(sim_name, host):
	simulation_instances = __sim_tracker_object[sim_name]._simulations
	count = 0
	for key, instance in simulation_instances.iteritems():
		if ( (str(instance._running_on_host) == str(host)) and (instance._schedule_time is None)):
			count = count + 1		
	return count	
	

def has_Finished(sim_name):
	return __sim_tracker_object[sim_name]._finished
	