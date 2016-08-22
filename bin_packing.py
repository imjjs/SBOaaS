from vsvbp.container import *
from vsvbp.heuristics import *
from vsvbp.measures import *

import logging


class Item:
     """ An item """
     def __init__(self, id, requirements):
         self.requirements = requirements[:]
         self.size = requirements[0]
         self.id = id
 
     def __repr__(self):
        return str(self.id) + ':' + str(self.size)
        
        
class Bin:
      """ A bin """
      def __init__(self, id, host, capacities):
          self.capacities = capacities[:]
          self.remaining = capacities[:]
	  self.host = host
          self.size = 0
          self.items = []
          self.id = id
  
      def __repr__(self):
          return str(self.id + ' : ' + str(self.items) + ' : ' + str(self.capacities))
  
      def feasible(self, item):
          """ Return True iff item can be packed in this bin """
          for req, rem in itertools.izip_longest(item.requirements,self.remaining):
              if (req > rem):
                  return False
          return True
  
      def insert(self, item):
          """
              Adds item to the bin
              Requires: the assignment is feasible
          """
          for i, req in enumerate(item.requirements):
              self.remaining[i] -= req
          self.items.append(item)
  
      def add(self, item):
          """
              Test feasibility and add item to the bin
              Return True if the item has been added, False o.w.
          """
          if self.feasible(item):
              self.insert(item)
              return True
          return False
  
      def empty(self):
          """ Empty the bin """
          self.items = []
          self.remaining = self.capacities[:]
        
	
def best_fit_decreasing(items, bins, extra_bins):
	    """
	    Pack items in selected bin.
		Sort items after each iteration
		(one iteration = one bin is consumed).

	    Return the list of unpacked items.
	    If all items have been packed, this list is empty.
	    Otherwise, failed[i] is a tuple (r,i). r is the rank of the item
	    (means r items have been tried before) and i is the item --
	    In the bin centric heuristic, failed[0][0] is the number of
	    items successfully packed
	    """
	    logging.debug("items: " + str(items))
	    logging.debug("bins: " + str(bins))

	    # create lists of bins and items
	    bi = deque(bins)
	    if (len(extra_bins)) == 0:
		logging.error('no extra bins')
		logging.error(str(items))
	    sizebin = extra_bins[0]
	    extra_bi = deque(extra_bins)

	    mapped_bins = []
	    new_bins = []
	    while bi or extra_bi:

		# Get smallest bin
		if len(bi) > 0:
			b = minl(bi)		        
		else:
			b = minl(extra_bi)		        


		# Sort items by decreasing order of their sizes
		sortl(items, dec=True)

		keep_going = True
		while keep_going:
		    keep_going = False

		    # Pack an item
		    for i in items:
			if b.add(i):
			    keep_going = True
			    items.remove(i) # VERY UNEFFICIENT !!!
			    break
		if b.id == "new":
			extra_bi.remove(b)
			if len(b.items) > 0:
				new_bins.append(b)
		else:
			bi.remove(b)
			if len(b.items) > 0:
				mapped_bins.append(b)

	    if len(items) != 0:
		logging.error('Cannot pack: ' + str(items) + ' on ' + str(sizebin))
		return None
		

	    return (new_bins, mapped_bins)
