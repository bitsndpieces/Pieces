from .policy import *

class file(Policy):
	def partition(self, firmware, clique):
		self.group_leaves(firmware, clique)
		self.dominator_merge(firmware, clique)
		self.pair_merge(firmware, clique)
		for f in clique["files"]:
			comp = firmware.create_compartment()
			for func in clique_filter(clique, firmware.files[f]):
				comp.add(func)
				if func in firmware.clique_filter_pdg(clique):
					for obj in clique_filter(clique, firmware.analysis.pdg.successors(func)):
						if obj not in firmware.funcfilemap:
							comp.add(obj)
						elif firmware.funcfilemap[obj] == firmware.funcfilemap[func]:
							comp.add(obj)
