#import frontend
#import analyzer
import analyze
import partition
import instrument
import shutil
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


analysis = analyze.run(input["firmware"])

firmware = partition.run(input, analysis)

instrument.run(input, firmware)
