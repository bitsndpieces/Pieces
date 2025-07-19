from .policy import *

class priv(Policy):
	def partition(self, firmware, clique):
		for obj in clique["objs"]:
			firmware.priv.add(obj)
