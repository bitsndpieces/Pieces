#import frontend
from analyzer.gen_pdg import *
import shutil
import partitioner.firmware_loader
import click
import utils
import sys
from utils import debug, print_help_msg
from dotenv import load_dotenv
from partitioner.llvm import Compiler
import os 

load_dotenv()
try:
	input = utils.load_config(standalone_mode=False)
	if not input:
		exit()
except Exception as e:
	print(e)
	utils.print_help_msg(utils.load_config)
	exit()

os.environ["P_OUT_DIR"] = os.path.abspath(os.environ["P_OUT_DIR"]) +"/"
os.makedirs(os.environ["P_OUT_DIR"], exist_ok=True)
input["firmware"]["bc"] =  os.path.abspath(input["firmware"]["bc"])
debug("Loading input firmware.")

analysis = run_analysis(input["firmware"])

#compiler = Compiler()
#compiler.analyze(input["firmware"])
firmware = partitioner.firmware_loader.Firmware(input["firmware"], analysis)
#from IPython import embed; embed()
#print(firmware.threads)
firmware.generate_cliques(input["firmware"])
firmware.merge_shared_compartments()
firmware.generate_dev_info()
firmware.sanitize()
firmware.write_partitions()
firmware.dump()

# create a file mapping functions to a compartment id
cmap = open("./compartmentMap", 'w')
compartmentIDs = {}
for function in firmware.compartmentMap:
	compartment = firmware.compartmentMap[function]
	if not compartment in compartmentIDs:
		compartmentIDs[compartment] = len(compartmentIDs)
	cid = compartmentIDs[compartment]
	cmap.write(f'{function}\t{cid}\n')
cmap.close()

cmd = [os.environ["SVF_BIN"] + "/svf-pieces", f'bc={input["firmware"]["bc"]}', '-instrument']
subprocess.run(cmd)

#new_bin= compiler.instrument(input["firmware"])
#compiler.disassemble(new_bin)
#shutil.copyfile(new_bin, input["firmware"]["bc"])
