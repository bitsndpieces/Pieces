from .policy import *

class thread(Policy):
	def partition(self, firmware, clique):
		self.group_leaves(firmware, clique)
		self.dominator_merge(firmware, clique)
		self.pair_merge(firmware, clique)

		for thread in clique_filter(clique, firmware.threads):
			if thread not in firmware.compartmentMap:
				compartment = firmware.create_compartment()
				compartment.add(thread)

		#Preprocessing might've put the threads in a comp already
		#so just bookeeping there won't help us.  
		tCompartments = []
		for thread in clique_filter(clique, firmware.threads):
			tCompartments.append(firmware.compartmentMap[thread])

		firmware.dump()
		self.expandComponentsX(tCompartments, firmware, clique)
		firmware.dump()
		self.assignLooseFunctions(firmware, clique)
		firmware.dump()
		self.mergeComponentsExcept(tCompartments, firmware, clique)
