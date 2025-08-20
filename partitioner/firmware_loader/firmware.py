from utils import *
from partitioner.policies import *
import os
from llvmlite import ir, binding

class Firmware:
	printDevUsage = False

	def __init__(self, config, analysis, llvm_data_dir=None):
		if llvm_data_dir is None:
			llvm_data_dir = os.environ["P_OUT_DIR"]
		self.config = config
		self.priv = self.create_compartment()
		self.bitcode = config["bc"]
		self.symex_bc = config["symex_bc"]
		self.platform = config["platform"]
		self.svd = config["svd"]

		self.analysis = analysis

		#Load function-file and data-file maps.
		self.funcfilemap = read_key_value_file(llvm_data_dir + os.environ["FILE_MAP_FILE"], os.environ["EC_DELIM"])
		#self.funcdirmap  = read_key_value_file(llvm_data_dir + os.environ["DIR_MAP_FILE"], os.environ["EC_DELIM"])
		self.datafilemap = read_key_value_file(llvm_data_dir + os.environ["DATA_MAP_FILE"], os.environ["EC_DELIM"])

		self.files = {}
		#Extract all files in the firmware
		for func in self.funcfilemap:
			if self.funcfilemap[func] not in self.files:
				self.files[self.funcfilemap[func]] = []
			self.files[self.funcfilemap[func]].append(func)
		for obj_elem in self.datafilemap:
			if self.datafilemap[obj_elem] not in self.files:
				debug(self.datafilemap[obj_elem] +"is a data only file")
				self.files[self.datafilemap[obj_elem]] = []

		#We don't need these yet
		'''
		self.funcdevmap = read_key_list_value_file(llvm_data_dir + os.environ["FUNC_DEV_MAP_FILE"], os.environ["EC_DELIM"])
		#create reverse map for device->function access
		#Note: dfmap = {v: k for k, v in fdmap.items()} #Only works for 1-1
		#thats why we do this way, TODO:maybe there's a better way fix later
		self.devfuncmap = create_reverse_list_map(self.funcdevmap)


		temp = open(llvm_data_dir + os.environ["FUNC_REACH_FILE"])
		self.threads_reach = {}
		current_thread =""
		for line in temp:
			if "	" in line:
				self.threads_reach[current_thread].append(line.strip())
			else:
				self.threads_reach[line.strip()] = []
				current_thread = line.strip()

		temp = open(llvm_data_dir + os.environ["HISTO_FILE"])
		self.fhisto = {}
		current_fun = ""
		for line in temp:
			if "	" in line:
				[fun,count] = line.strip().split(":")
				self.fhisto[current_fun][fun] = int(count)
			else:
				self.fhisto[line.strip()] = {}
				current_fun = line.strip()

		#Create a coarse grained map for devices. TODO: This was 
		#required in early days when we didn't parse SVD check if we still need it.
		self.devfuncmapCoarse = {}
		for addr in self.devfuncmap:
			base = int(addr, 0) & 0xFFFFF000
			if base in self.devfuncmapCoarse:
				self.devfuncmapCoarse[base] = self.devfuncmapCoarse[base]  + self.devfuncmap[addr]
			else:
				self.devfuncmapCoarse[base] = self.devfuncmap[addr]
		'''
		#Finally see if PDG is missing something
		for func in self.funcfilemap:
			if func not in self.analysis.pdg.nodes:
				self.analysis.pdg.add_node[func]

		#self.ignore_funcs(llvm_data_dir)
		self.total_objects = len(self.analysis.pdg)# + len(self.analysis.pddg)
		self.compartments = []
		self.compartmentMap = {}

		self.os = config["os"]

		#Not yet needed for current partition policies
		'''
		self.threads = read_line_vector_file(llvm_data_dir + os.environ["THREADS_FILE"])

		devices = []
		self.svdfmap = {} #Map SVD tuples to devices
		handle = getSVDHandle(self.platform, self.svd)
		for addr in self.devfuncmap:
			dev,base,size = getDevice(addr, handle)
			if dev is None:
				name = "unkown"
			else:
				name = dev.name
			if (name,base,size) not in devices:
				devices.append((dev,base,size))
			if (name,base,size) in self.svdfmap:
				for f in self.devfuncmap[addr]:
					if f not in self.svdfmap[(name,base,size)]:
						self.svdfmap[(name,base,size)].append(f)
			else:
				self.svdfmap[(name,base,size)] = []
				for f in self.devfuncmap[addr]:
					self.svdfmap[(name,base,size)].append(f)


		self.svdmap={}
		#Create a func map.
		for fun in self.analysis.pdg:
			self.svdmap[fun] = []
			if fun in self.funcdevmap:
				for addr in self.funcdevmap[fun]:
					periph,base,size = getDevice(addr, handle);
					#Let's create a new device SVD's are not super reliable IMO
					if periph==None:
						base = addr
						size = 0x1000
					if (periph,base,size) not in self.svdmap[fun]:
						self.svdmap[fun].append((periph,base,size))
	
		if True:
			for dev,base,size in self.svdfmap:
				if dev == "unkown":
					continue
				debug(dev + " used by:")
				for fun in self.svdfmap[(dev,base,size)]:
					debug(" " + str(fun))
			debug(str(len(self.svdfmap)) + " devices found")
		'''
		return


	def ignore_funcs(self, llvm_data_dir):
		il = read_line_vector_file(llvm_data_dir + os.environ["IGNORE_LIST"])
		for ignore in il:
			if ignore in self.analysis.cfg.nodes:
				self.analysis.cfg.remove_node(ignore)
			if ignore in self.analysis.pddg.nodes:
				self.analysis.pddg.remove_node(ignore)
			if ignore in self.analysis.pdg.nodes:
				self.analysis.pdg.remove_node(ignore)


	#Use the visitor pattern to generate compartment.
	def create_compartment(self):
		return Firmware.Compartment(self)
	
	def clique_filter_pdg(self, clique):
		return (obj for obj in self.analysis.pdg.nodes if obj in clique["objs"])
	
	def clique_filter_files(self, clique):
		return (obj for obj in self.files if obj in clique["files"])

	# Class for compartment tracking, in future we could have mulitple firmwares as input, so it is better to 
	# contain each compartment metadata within its own firmware
	class Compartment():
		def __init__(self, firmware):
			self.objs = []
			self.firmware = firmware
	
		def __del__(self):
			for obj in self.objs:
				self.remove(obj)
			if self in self.firmware.compartments:
				self.firmware.compartments.remove(self)

		def __contains__(self, key):
			return key in self.objs


		def __append(self, item):
			self.objs.append(item)

		def __str__(self):
			return str(self.objs)
				

		def __iter__(self):
			return iter(self.objs)

		def __next__(self):
			return next(self)

		def __len__(self):
			return len(self.objs)

		def add(self, obj):
			#Is object already in another compartment, remove it.
			if obj in self.firmware.compartmentMap:
				if self.firmware.compartmentMap[obj]==self:
					return
				oldCompartment = self.firmware.compartmentMap[obj]
				oldCompartment.remove(obj)
			self.__append(obj)
			self.firmware.compartmentMap[obj] = self
			if self not in self.firmware.compartments:
				self.firmware.compartments.append(self)
	
		def remove(self, obj):
			self.objs.remove(obj)
			if len(self.objs) == 0:
				 self.firmware.compartments.remove(self)
	
		def mergeCompartments(self, compartment2):
			for fun in list(compartment2.objs):
				self.add(fun)

		def mergeComponentsExcept(self, tCompartments):
			comp = Compartment(self.firmware)
			objlist =[]
			for compartment in list(self.firmware.compartments):
				if compartment not in tCompartments:
					for obj in list(compartment.objs):
						comp.add(obj)

	def generate_cliques(self, config):
		self.cliques= []
		members = {}
		clique_id = 0
		cliques = config["cliques"]
		policies = []
		for clique in cliques:
			dir = cliques[clique]["dir"]
			policy = config_to_class(cliques[clique]["policy"])()
			if type(policy) not in policies:
				policies.append(type(policy))
			current_files = {}
			current_objs = []
			current_clique = {}
			for file in self.files:
				if dir in file:
					current_files[file] = self.files[file]
			for file in current_files:
				for obj in current_files[file]:
					current_objs.append(obj)
					
			current_clique["files"] = current_files
			current_clique["objs"] = current_objs
			current_clique["name"] = cliques[clique]["name"]
			self.cliques.append(current_clique)
			members.update(current_files)
			debug("Members for " + clique)
			policy.partition(self, current_clique)

		background_clique = {}
		current_files = {}
		current_objs = []
		for file in self.files:
			if file not in members:
				current_files[file] = self.files[file]
				
		for file in current_files:
			for obj in current_files[file]:
				current_objs.append(obj)
		policy = config_to_class(config["background_policy"])()
		if type(policy) not in policies:
			policies.append(type(policy))
		background_clique["files"] = current_files
		background_clique["objs"] = current_objs
		background_clique["name"] = "background_clique"
		self.cliques.append(background_clique)
		debug("Last background clique")
		policy.partition(self, background_clique)

		#run finalizers
		for policy in policies:
			obj = policy()
			obj.finalizer(self)

	def dump(self):
		debug("Number of compartments: "+ str(len(self.compartments)))
		frozen = jsonpickle.encode(self, indent=4)
		with open(os.environ["P_OUT_DIR"] + "firmware", "w") as f:
			f.write(frozen)

	def find_clique(self, obj):
		for clique in self.cliques:
			if obj in clique["objs"]:
				return clique
	def clique_consistent(self, objA, objB):
		return self.find_clique(objA) == self.find_clique(objB)

	def merge_shared_compartments(self):
		Merge = True
		Error = False
		while(Merge):
			Merge =  False
			for var in self.analysis.pddg.nodes(data=True):
				if var[1]['type'] == 'function':
					continue

				compartment = None
				#Check for all users of this data
				ogFunc = None
				for func in self.analysis.pddg.successors(var[0]):
				#Is this the first user compartment?
					if ogFunc is None:
						#Make this the big compartment, everything will be merged into it.
						ogFunc = func
					if self.compartmentMap[ogFunc] != self.compartmentMap[func]:
						if self.clique_consistent(func, ogFunc):
							warn("Merging for shared data:" + var[0])
							self.compartmentMap[ogFunc].mergeCompartments(self.compartmentMap[func])
						else:
							error("Invalid Clique Configuration for variable:" + var[0])
							Error = True
						warn("Users:")
						warn("	Clique: " + self.find_clique(func)["name"])
						warn("	" + func)
						warn("	" +"Clique: " + self.find_clique(ogFunc)["name"])
						warn("	" +ogFunc)
						if Error:
							sys.exit(1)
						Merge = True
	
	def sanitize(self):
		for var in self.analysis.pddg.nodes(data=True):
			if var[1]['type'] == 'function':
				continue

			ogFunc = None
			for func in list(self.analysis.pddg.successors(var[0])):
				if ogFunc is None:
					ogFunc = func
				if self.compartmentMap[ogFunc] != self.compartmentMap[func]:
					error("Resource sharing between compartments")
					error("For data:" + var[0])
					error(ogFunc)
					error(func)

	def generate_dev_info(self):
		self.compartmentDevMap = {}
		for compart in self.compartments:
			self.compartmentDevMap[compart]={}

		return #not implemented yet
		for compart in self.compartments:
			for fun in compart:
				if fun in self.svdmap:
					for dev in self.svdmap[fun]:
						if dev is not None:
							self.compartmentDevMap[compart][dev] = 1


	def write_partitions(self):
		with open(os.environ["P_OUT_DIR"] + ".policy", 'w') as f:
			if len(self.priv) == 0:
				f.write("[]" + "\n")
			for compartment in self.compartments:
				f.write(str(compartment) + "\n")

		'''
		with open(os.environ["P_OUT_DIR"] + ".dev", 'w') as f:
			for fun in self.analysis.pdg:
				f.write(fun +" uses: \n")
				for dev in self.svdmap[fun]:
					if dev[0] is not None:
						f.write("   " +str(dev[0].name) +"\n")
		'''

		rtdev  = open(os.environ["P_OUT_DIR"] + "rtmk.dev", "w")
		with open(os.environ["P_OUT_DIR"] + "rtmk.devautogen", "w") as rtdeva:
			miss = False
			#			self.compartmentDevMap[compart][dev] 
			#Old code: 	compartmentDevMap[i][dev]
			i =0
			for comp in self.compartmentDevMap:
				numDev =0
				compart = self.compartmentDevMap[comp]
				rtdev.write("Compartment ID:" + str(i))
				minBase = 0x60000000
				maxBase = 0x40000000
				for dtuple in compart:
					numDev  = numDev + 1
					dev, base, size = dtuple
					if dev is not None:
						rtdev.write(dev.name + ":" +hex(base)+ ":"+ hex(size))
					else:
						#Missing this device info
						miss = True
					rtdev.write("\n")
				someDev = False
				for dtuple in compart:
					dev, base, size = dtuple
					if dev is not None:
						someDev = True
						start = base
						end = base +size
						if (i==30):
							debug(hex(minBase))
							debug(hex(maxBase))
						if start < minBase:
							minBase = start
							if (i==30):
									print(hex(minBase))
						if end > maxBase:
							maxBase = end
							
				if someDev == False:
					minBase= 0x40000000
					maxBase = 0x40000000

				if minBase==0x60000000:
					for dtuple in compart:
						dev, base, size = dtuple
						if dev is not None:
							debug("Unknown device:")
							debug(dev.name)
							debug(hex(base))
							debug(hex(size))

						
				rtdeva.write(hex(minBase) + "," + hex(maxBase - minBase) +"," +hex(maxBase) + "\n")
				rtdev.write("Number of devices:" + str(numDev) +"\n")
				i = i+1
