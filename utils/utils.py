import jsonpickle
import os
import sys
import subprocess
import json
import click
from   cmsis_svd.parser import SVDParser

DEBUG_ON = False
class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKCYAN = '\033[96m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'
	RED = '\033[91m'
	GREEN = '\033[92m'
	YELLOW = '\033[93m'
	BLUE = '\033[94m'
	MAGENTA = '\033[95m'
	CYAN = '\033[96m'


def getSVDHandle(oem,model):
	return SVDParser.for_packaged_svd(oem, model).get_device().peripherals

def getDevice(addr, peripherals):
	addr = int(addr, 16)
	# Make sure this is a device, this is a possible circumvent around the enforced protections
	# a malicious program can hardcode to other compartment's memory, make sure we don't allow it
	if not (addr>= 0x40000000 and addr <=0x60000000):
		#print("Private region or protected region used:" + hex(addr))
		return None, 0, 0
	for peripheral in peripherals:
		if  peripheral._address_block is not None:
			if ((addr >= peripheral.base_address) and (addr < (peripheral.base_address + peripheral._address_block.size))):
				return peripheral, peripheral.base_address, peripheral._address_block.size
		elif peripheral.get_derived_from():
			derivedFrom = peripheral.get_derived_from()
			if derivedFrom._address_block is not None:
				if ((addr >= peripheral.base_address) and (addr < (peripheral.base_address + derivedFrom._address_block.size))):
						return peripheral, peripheral.base_address, derivedFrom._address_block.size
		elif peripheral.size is not None:
			if ((addr >= peripheral.base_address) and (addr < (peripheral.base_address + peripheral.size))):
				return peripheral, peripheral.base_address, peripheral.size

	debug("Device not found:" + hex(addr))
	return None, 0, 0


def print_help_msg(command):
	with click.Context(command) as ctx:
		click.echo(command.get_help(ctx))

@click.command()
@click.argument('conf', type=click.File('r'))
def load_config(conf):
	""" External partitioner Engine for firmware"""
	return json.load(conf)


def debug(msg):
	if DEBUG_ON:
		print(msg)

def colorize(text, color):
	return color + text + bcolors.ENDC
def warn(msg):
	print(bcolors.WARNING+ "WARN:" + bcolors.ENDC+msg)

def error(msg):
	print(bcolors.FAIL + "ERROR:" + bcolors.ENDC+ msg)


def clique_filter(clique, objs):
	return (obj for obj in objs if obj in clique["objs"])

def read_line_vector_file(input_file):
	with open(input_file) as f:
			out = f.read().splitlines() 
	return out

def read_key_value_file(input_file, delimiter):
	out ={}
	with open(input_file) as f:
			lines = f.readlines()
			for line in lines:
				line = line.replace("\n","")
				[key, value] = line.split(delimiter)
				out[key] = value
	return out

def read_key_list_value_file(input_file, delimiter):
	out = {}
	with open(input_file) as f:
		lines = f.readlines()
		for line in lines:
			line = line.replace("\n", "")
			[key, value] = line.split(delimiter)
			if key in out:
				out[key].append(value)
			else:
				out[key] =[value]
	return out

def create_reverse_list_map(input_map):
	out = {}
	for f in input_map:
		for elem in input_map[f]:
			if elem in out:
				if f not in out[elem]:
					out[elem].append(f)
			else:
				out[elem] = [f]
	return out

sub_commands = 0
def run_cmd(cmd, out=subprocess.DEVNULL, cwd_arg=None, shell=False):
	global sub_commands
	f= None
	debug("Runing" + str(cmd) + " in " + str(cwd_arg))
	if cwd_arg==None:
		cwd_arg=os.environ["P_OUT_DIR"]
	if  out==subprocess.STDOUT:
		p = subprocess.Popen(cmd, cwd=cwd_arg)
	elif out==subprocess.DEVNULL:
		exe = os.path.basename(cmd[0])
		f = open(os.environ["P_OUT_DIR"] + exe + str(sub_commands), "w")
		sub_commands +=1
		p = subprocess.Popen(cmd, stdout=f, stderr=f, shell=shell, cwd=cwd_arg)
		f.write("Command used: \n")
		f.write(str(" ".join(cmd)))
		f.write("CWD: \n")
		f.write(str(cwd_arg))
	else:			
		p = subprocess.Popen(cmd, stdout=out, stderr=out, shell=shell, cwd=cwd_arg)
	p.wait()
	debug("Ran" + str(cmd) + " in " + str(cwd_arg))
	if p.returncode != 0:  
		debug("Command didn't succeed:")
		debug(" ".join(cmd))
		debug("Return Code:" + str(p.returncode))
#if out!= subprocess.DEVNULL:
#			out.seek(0)
#			debug(out.read())
		sys.exit(1)

	if f:
		f.close()

def config_to_class(classname):
	return getattr(sys.modules["partitioner.policies."+classname], classname)
