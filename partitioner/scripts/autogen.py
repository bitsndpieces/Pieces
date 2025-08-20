#!/usr/bin/python3
import subprocess
import buildutils
import os
import sys
import re
import math
from pathlib import Path

DEBUG_FLAG = True
NUM_DEFAULT_COMPARMENTS = 20

def get_lma_vma_from_objdump(elf_file):  #ToDo: Move this to binutils
	# Check if the file exists
	if not os.path.isfile(elf_file):
		raise FileNotFoundError(f"The file '{elf_file}' does not exist.")

	# Run arm-none-eabi-objdump to get section headers
	try:
		result = subprocess.run(
			['arm-none-eabi-objdump', '-h', elf_file],
			stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
		)
	except subprocess.CalledProcessError as e:
		raise RuntimeError(f"Error running objdump: {e.stderr}")

	# Dictionary to store sections' LMA and VMA
	sections = {}

	# Parse the objdump output
	lines = result.stdout.splitlines()

	# Flag to indicate whether we are parsing a section header
	parsing_section = False


	for line in lines:
		# Look for section header lines (those starting with space and not starting with a number or "Idx")

		if line.strip() and line.strip()[0].isdigit():
			# Extract the section's name, VMA, and LMA
			parts = line.split()
			if len(parts) == 7:  # Ensure there's enough data in the line
				section_name = parts[1]
				vma = parts[3]  # VMA is in the 4th column
				lma = parts[4]  # LMA is in the 5th column
				sections[section_name] = {'VMA': vma, 'LMA': lma}

		# Skip section attribute lines (those that don't start with numbers and are indented)
		# These lines describe section flags like CONTENTS, ALLOC, LOAD, etc.
		elif line.strip() and not line[0].isdigit():
			continue

	# If no sections found, raise an error
	if not sections:
		raise ValueError("No sections found in the ELF file.")

	return sections

def check_mpu_constraints(size, address):
	flag = True
	if size != 0:
		# Ensure size is a power of 2 and at least 32 bytes (Constraint 1 and 2)
		if size < 32 or not isPowerOfTwo(size):
			flag = False

		# Ensure base address is a multiple of the new size (Constraint 3)
		if address % size != 0:
			flag = False
	
	if flag:
		print(f"size: {size}, addr: {address} follow MPU constraints")
	else:
		print(f"size: {size}, addr: {address} do not follow MPU constraints")

	return flag


def find_sizeinfo_file():
	return [str(file) for file in Path(".").rglob("sizeinfo")]

def parse_sizeinfo(file_path):
	sections = {}
	total_size = 0
	
	with open(file_path, 'r') as file:
		for line in file:
			match = re.match(r'^(\S+)\s+(\d+)\s+(\d+)?$', line.strip())
			if match:
				section_name = match.group(1)
				size = int(match.group(2))
				addr = int(match.group(3)) if match.group(3) else None
				
				sections[section_name] = {"size": size, "addr": addr}
			elif line.startswith("Total"):
				total_size = int(line.split()[-1])
	
	return {"sections": sections, "total_size": total_size}

def get_num_compartments():
	script_dir = os.path.dirname(os.path.abspath(__file__))
	file_path = os.path.join(script_dir, "../out/.policy")

	try:
		with open(file_path, "r") as file:
			line_count = sum(1 for _ in file)
	except FileNotFoundError:
		print("BUGON: Wrong phase discovery?")
		line_count = NUM_DEFAULT_COMPARMENTS
	except Exception as e:
		print(f"An error occurred: {e}")
	return line_count

def find_phase(env):
	#Linker script is not given
	if "LD_OVERLAY" not in env:
		return 0

	#Firmware is not partitioned
	script_dir = os.path.dirname(os.path.abspath(__file__))
	file_path = os.path.join(script_dir, "../out/.policy")
	if not os.path.exists(file_path):
		return 1

	#Firmware objects no instrumented
	#TODO: What if more files?
	files = find_sizeinfo_file()
	if (len(files) == 0):
		return 1
	sizeinfo = parse_sizeinfo(files[0])

	total_partitioned_code =0
	if DEBUG_FLAG:
		print(sizeinfo)

	for section in sizeinfo["sections"].keys():
		if "csection" in section:
			total_partitioned_code += sizeinfo["sections"][section]["size"]

	if total_partitioned_code == 0:
		return 2
	else:
		return 3

def run_setupld(env, num_comps):
	command = [
		"setupLD.py", #For the path issue
		"-n", str(num_comps),
		"-l", env["LD_OVERLAY"],
		"-c", directory + "/autogen_data.c",
		"-H", directory + "/autogen_heap.c"
	]

	# Run the command
	try:
		result = subprocess.run(command, check=True, text=True, capture_output=True)
		
		if DEBUG_FLAG:
			print("STDOUT:", result.stdout)
			print("STDERR:", result.stderr)
	except subprocess.CalledProcessError as e:
		print("Error occurred while running the command:")
		print(e.stderr)

def next_power_of_2(n):
    return 1 if n == 0 else 2**math.ceil(math.log2(n))

def get_sections_line_index(lines):
    for index, line in enumerate(lines):
        if "SECTIONS" in line:
            return index
    return -1  # Return -1 if SECTIONS is not found

def Log2(x):
	return (math.log10(x) /
			math.log10(2))

def isPowerOfTwo(n):
    return (math.ceil(Log2(n)) == math.floor(Log2(n)))

def fixLMAAndVMA(size, vma, lma):    
	if size != 0:
		# Ensure size is a power of 2 and at least 32 bytes (Constraint 1 and 2)
		if size < 32 or not isPowerOfTwo(size):
			new_size = max(next_power_of_2(size), 32)
			if DEBUG_FLAG:
				print(f"Adjusting size of : {size} -> {new_size}")
			size = new_size

		# Ensure base address is a multiple of the new size (Constraint 3)
		if vma % size != 0:
			new_vma = ((vma // size)+1) * size
			if DEBUG_FLAG:
				print(f"Adjusting address of : {vma} -> {new_vma}")
			vma = new_vma
		
		# Ensure base address is a multiple of the new size (Constraint 3)
		if lma % size != 0:
			new_lma = ((lma // size)+1) * size
			if DEBUG_FLAG:
				print(f"Adjusting address of : {lma} -> {new_lma}")
			lma = new_lma
	return size, vma, lma

def adjust_sections(linker_script, section_info, project_binary_path):

	lma_vma_addr_secs = get_lma_vma_from_objdump(project_binary_path)

	code_sections_start = 0
	compartment_code_counter = 0 
	compartment_code_offset = 0
	cprev_sec_end_addr = 0
	oprev_vma_end_addr = 0
	new_file_lines = []

	ram_location_counter=0
	flash_location_counter=0

	with open(linker_script, 'r') as file:
		lines = file.readlines()
    
	sections_start = get_sections_line_index(lines)
    
	index = 0
	while index < len(lines):

		# Phase 1: Copy everything until sections start
		line = lines[index]
		new_file_lines.append(line)
		
		if index <= sections_start:
			index += 1
			continue
		
		# Phase 2: This means that we are inside data section in SECTIONS
		if  "osection" in line and ":" in line: #ToDo: Use Regex
			# Handle MPU address constraints logic
			text = lines[index]
			if ":" in text:
				extracted_section_text = text.split(":")[0].split()[0]
			else:
				index += 1
				continue

			# Load flash_location_counter with end of flash address of .data 
			# i.e. LOADADDR(.data) + SIZEOF(.data)
			if extracted_section_text == ".osection0data":
				flash_location_counter = int(lma_vma_addr_secs['.data']['LMA'], 16) + section_info['.data']['size']
				ram_location_counter = int(lma_vma_addr_secs['.data']['VMA'], 16) + section_info['.data']['size']
				lma = flash_location_counter
				if (DEBUG_FLAG):
					print(f"flash_location_counter: {flash_location_counter}")
					lma_osection0data = int(lma_vma_addr_secs['.osection0data']['LMA'], 16)
					print(f"lma_osection0data:{lma_osection0data}")
					lma_osection0 = int(lma_vma_addr_secs['.osection0']['LMA'], 16)
					print(f"lma_osection0:{lma_osection0}")
					lma_csection0 = int(lma_vma_addr_secs['.csection0']['LMA'], 16)
					print(f"lma_csection0data:{lma_csection0}")

            # This is where we should handle our location counter logic
			osection = re.search(r"\.osection\d+", extracted_section_text).group()

			size_1 = section_info[extracted_section_text]["size"]
			size_2 = section_info[osection]["size"]
			size = size_1 + size_2
			vma = section_info[extracted_section_text]["addr"]

			if vma < oprev_vma_end_addr:
				vma = oprev_vma_end_addr
			lma=lma+size

			fixed_size, fixed_vma, fixed_lma = fixLMAAndVMA(size, vma, lma)
			if (DEBUG_FLAG):
				print(f"extracted_section_text: {extracted_section_text}, osection: {osection}")
				print(f"size, vma, lma {size}, {vma}, {lma}")
				print(f"fixed_size, fixed_vma, fixed_lma {fixed_size}, {fixed_vma}, {fixed_lma}")

			ram_padding = fixed_vma - vma + fixed_size - size
			flash_location_counter=flash_location_counter+size#+ram_padding

			osectionNdata = f"\t {extracted_section_text} ({fixed_vma}) : AT (COMPARTMENT_DATA_START + COMPARTMENT_DATA_COUNTER)\n"
			new_file_lines[-1] = osectionNdata

			index = index+1
			new_file_lines.append(lines[index])

			while(":" not in lines[index]): #ToDo: Use Regex
				index = index +1
				new_file_lines.append(lines[index])

			osectionN = f"\t{osection} : AT ({fixed_vma} + SIZEOF({extracted_section_text}))"
			new_file_lines[-1] = osectionN

			while("}" not in lines[index]):
				index = index +1
				new_file_lines.append(lines[index])
			
			vma_end_addr = fixed_vma + fixed_size
			if (DEBUG_FLAG):
				print(f"vma_end_addr, fixed_vma, size: {vma_end_addr}, {fixed_vma}, {fixed_size}")
			end_location_counter = "\t\t. = " + str(vma_end_addr) + " ;\n"
			new_file_lines.insert(len(new_file_lines) - 2, end_location_counter)
			oprev_vma_end_addr = vma_end_addr
            
			code_sections_start = flash_location_counter
			if (DEBUG_FLAG):
				print(f"flash_location_counter {flash_location_counter}")
				print(f"osection: {osection} vma_end_addr {vma_end_addr}")
				print(f"lma: {lma}, size: {size}, total: {lma+size}")

		# Phase 3: This means that we are inside code section in SECTIONS
		if  "csection" in line and "CODE_SECTIONS_START" in line and ":" in line:  #ToDo: Use Regex 

			location_counter_base=code_sections_start+compartment_code_counter
			location_counter = location_counter_base
			if (DEBUG_FLAG):
				print(f"location_counter: {location_counter}")

			# Check it it is the first section
			# Handle MPU address constraints logic
			text = lines[index]
			first_item_line = text.split()[0]

			size = section_info[first_item_line]["size"]
			clma = location_counter
			cvma = location_counter

			fixed_csize, fixed_cvma, fixed_clma = fixLMAAndVMA(size, cvma, clma)
			if (DEBUG_FLAG):
				print(f"section {first_item_line}")
				print(f"size, cvma, clma: {size}, {cvma}, {clma}")
				print(f"fixed_csize, fixed_cvma, fixed_clma: {fixed_csize}, {fixed_cvma}, {fixed_clma}")
				el_addr = int(lma_vma_addr_secs['.osection2data']['LMA'], 16) + section_info['.osection2data']['size']
				print(f"lma from bin: {el_addr}")

			offset = fixed_clma-clma
			compartment_code_offset = compartment_code_offset + offset
			line = first_item_line + f" (CODE_SECTIONS_START + COMPARTMENT_CODE_COUNTER + {hex(compartment_code_offset)} ) : AT(CODE_SECTIONS_START + COMPARTMENT_CODE_COUNTER + {hex(compartment_code_offset)} )\n"
			
			new_file_lines[-1] = line

			end_location_counter = f"\t\t . =  (CODE_SECTIONS_START + COMPARTMENT_CODE_COUNTER + {hex(compartment_code_offset)} ) + {hex(fixed_csize)};\n"

			while("}" not in lines[index]):
				index = index +1
				new_file_lines.append(lines[index])
            
			new_file_lines.insert(len(new_file_lines) - 2, end_location_counter)
			compartment_code_counter = compartment_code_counter + offset + fixed_csize

		index += 1

	with open(linker_script, 'w') as new_file:
		new_file.writelines(new_file_lines)

def fix_mpu_reqs(env):
	size_info_file = find_sizeinfo_file()[0] # Fix find_sizeinfo_file func to return the file path
	sizeinfo = parse_sizeinfo(size_info_file)
	linker_file = env["LD_OVERLAY"].replace("overlay","ld")  #Fix ld file path
	project_binary_path = env["PHASE2_BINARY"]

	adjust_sections(linker_file, sizeinfo["sections"], project_binary_path)


directory = "autogen"
env = buildutils.load_project_meta()
phase = find_phase(env)
print("We are in phase:" + str(phase))


if phase ==0:
	if len(sys.argv) > 1:
		print("Command-line arguments provided:", sys.argv[1:])
		env = {}
		env["LD_OVERLAY"] = sys.argv[1]
		buildutils.save_project_meta(env)
		if not os.path.exists(directory):
			os.makedirs(directory)
	else:
		print("Project not initialized, please specify the overlay file")
		print("autogen.py ./scripts/mps2_m3.overlay")
		exit()

if phase ==1:
	run_setupld(env, 20)

	if 'LD_MOD_TIME' in env:
		buildutils.remove_key_from_pickle('LD_MOD_TIME')

if phase ==2:
	run_setupld(env, get_num_compartments())
	print("Heap config is updated after this step. Rebuild the bitcode and run the analysis again.")

if phase ==3:
	
	if "PHASE2_BINARY" not in env:
		if len(sys.argv) > 1:
			print("Command-line arguments provided:", sys.argv[1:])
			env["PHASE2_BINARY"] = sys.argv[1]
			buildutils.save_project_meta(env)
			if not os.path.exists(directory):
				os.makedirs(directory)
		else:
			print("Phase 2 project binary not provided, please specify the phase 2 project binary")
			print("autogen.py ./build/RTOSDemo.axf")
			exit()

	linker_file = env["LD_OVERLAY"].replace("overlay","ld")
	if 'LD_MOD_TIME' in env:
		current_mod_time = os.path.getmtime(linker_file)
		if env["LD_MOD_TIME"] == current_mod_time:
			print("Linker script has not been modified!!!")
		else:
			print("Linker script has been modified after phase 3. Run from start again.")
		exit()

	fix_mpu_reqs(env)
	env["LD_MOD_TIME"] = current_mod_time = os.path.getmtime(linker_file)
	print("Generated new linkerscript.")
	print("Changed metadata: ", env)
	buildutils.save_project_meta(env)

	




