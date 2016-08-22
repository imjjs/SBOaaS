class NoCapacityException(Exception):
    def __init__(self):
        Exception.__init__(self, "No capacity in the cluster") 


class DeadlineMissedException(Exception):
    def __init__(self):
        Exception.__init__(self, "Sorry, the deadline missed !!!")
