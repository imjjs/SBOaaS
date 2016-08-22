# Need to document
class Host:

	def __init__(self, **kwargs):
        	self.__dict__ = kwargs
        	
	def __repr__(self):
		return str(self.__dict__)
	
class SimulationSlot:

	def __init__(self, **kwargs):
        	self.__dict__ = kwargs
	
	def __repr__(self):
		return str(self.__dict__)
	
        	
class ResourceAllocationInput:

	def __init__(self, **kwargs):
        	self.__dict__ = kwargs

	def __repr__(self):
		return str(self.__dict__)
	
        	
class SimulationsModel:

	def __init__(self, **kwargs):
        	self.__dict__ = kwargs
	
	def __repr__(self):
		return str(self.__dict__)
	

class SimulationResource:

	def __init__(self, **kwargs):
        	self.__dict__ = kwargs
	
	def __repr__(self):
		return str(self.__dict__)

class SimulationInstanceModel:

	def __init__(self, **kwargs):
        	self.__dict__ = kwargs

	def __repr__(self):
		return str(self.__dict__)
	
class SimulationTask:

	def __init__(self, **kwargs):
        	self.__dict__ = kwargs

	def __repr__(self):
		return str(self.id)
	

class SimulationTaskContainer:

	def __init__(self, **kwargs):
        	self.__dict__ = kwargs

	def __repr__(self):
		return str(self.__dict__)
