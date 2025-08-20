#!/usr/bin/python3

import sys, getopt
import math
from elftools.elf.elffile import ELFFile
import struct
import io

fragmentation=0
arch = "armv7m"

import subprocess
import os

def get_lma_vma_from_objdump(elf_file):
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


#TODO
def update_section_lma(elf_file_path, section_name, new_lma):
	try:
		# Open the ELF file in binary mode for reading
		with open(elf_file_path, 'rb') as f:
			elf = ELFFile(f)
			# Read the entire ELF file into memory as raw bytes
			elf_bytes = bytearray(f.read())

			# Get the section headers offset and size
			sh_offset = elf.header['e_shoff']
			sh_size = elf.header['e_shentsize']
			num_sections = elf.header['e_shnum']

			# Find the section header index for the section we want to modify
			section_index = None
			for i, section in enumerate(elf.iter_sections()):
				if section.name == section_name:
					section_index = i
					break

			if section_index is None:
				print(f"Section '{section_name}' not found.")
				return

			# Calculate the byte offset of the target section header
			section_header_offset = sh_offset + section_index * sh_size

			# The field we want to update is 'sh_addr' (LMA), which is at offset 0x18 for 32-bit ELF files.
			# For 64-bit ELF files, it's at offset 0x20. The exact offset depends on the architecture.
			lma_offset = section_header_offset + 0x18  # 0x18 is the offset for sh_addr in 32-bit ELF

			# Pack the new LMA as bytes
			new_lma_bytes = struct.pack('<I', new_lma)  # '<I' is for 32-bit little-endian format

			# Update the LMA in the raw ELF data
			elf_bytes[lma_offset:lma_offset+len(new_lma_bytes)] = new_lma_bytes

			# Write the modified ELF data to a new file
			new_elf_file_path = 'modified_' + elf_file_path
			with open(new_elf_file_path, 'wb') as new_file:
				new_file.write(elf_bytes)

			print(f"LMA of section '{section_name}' updated to {hex(new_lma)}.")
			print(f"Modified ELF file saved to: {new_elf_file_path}")

	except Exception as e:
		print(f"Error: {e}")

# Function to check
# Log base 2
def Log2(x):
	return (math.log10(x) /
			math.log10(2));
def isPowerOfTwo(n):
	return (math.ceil(Log2(n)) == math.floor(Log2(n)));
sizeRegionMap= { 0:"0", 32: "REGION_32B", 64: "REGION_64B", 128: "REGION_128B", 256: "REGION_256B", 512: "REGION_512B", 1024: "REGION_1K", 2048: "REGION_2K", 4096: "REGION_4K", 8192:"REGION_8K", 16384: "REGION_16K", 32768: "REGION_32K", 65536: "REGION_64K", 131072: "REGION_128K", 262144: "REGION_256K", 524288: "REGION_512K", 1048576: "REGION_1M", 2097152:"REGION_2M", 4194304:"REGION_4M",8388608:"REGION_8M",16777216:"REGION_16M",33554432:"REGION_32M",67108864:"REGION_64M",134217728:"REGION_128M",268435456:"REGION_256M",536870912:"REGION_512M",1073741824:"REGION_1G",2147483648:"REGION_2G",4294967296:"REGION_4G"}
	

def valid(base, size):
	if size != 0:
		upSize = size
		print("Is power of two?" + str(isPowerOfTwo(size)))
		if not isPowerOfTwo(size):
				upSize = 2 ** math.ceil(Log2(size))
				print(upSize - size)
		size = upSize 
		if base %size:
			print("Target base address is not divisible!")
			div = base/size
			div +=1
			newOffset = size *div
			print(newOffset)
		if size<32:
			print("Is less than 32 bytes")
	return [base, size]
def writeCodeSections(cpatch, csections):
	i = 0
	cs = ".csection"
	for section in range(len(csections)):
				cpatch.write("  .csection"+str(i) +" : \n")
				cpatch.write("  {\n")
				cpatch.write("  . = "+ str(csections[cs + str(section)][1]) +";\n")
				cpatch.write("_scsection"+str(i)+" = .;\n")
				cpatch.write("	*(.csection"+str(i)+")\n")
				cpatch.write("	. = "+ str(csections[cs + str(section)][0] + csections[cs + str(section)][1])+";\n")
				cpatch.write("_ecsection"+str(i)+" = .;\n")
				if arch=="armv7m":
					cpatch.write("  } > FLASH \n")
				else:
					cpatch.write("  }")
				i +=1

def writeDataSections(dpatch, dsections):
	i =0
	os = ".osection"
	for section in range(len(dsections)):
				dpatch.write("  .osection"+str(i) +"data : /* AT ( _sidata ) */\n")
				dpatch.write("  { . = ALIGN(4); \n")
				dpatch.write("  *(.osection" +str(i)+"data)		   /* .data sections. */\n")
				dpatch.write("  . = ALIGN(4); \n")
				dpatch.write("  _eosection"+str(i) + "data = .;\n")
				dpatch.write("} > RAM AT > FLASH\n")
				dpatch.write("_sosection"+str(i) + "data = LOADADDR(.osection"+str(i) + "data);\n")
				dpatch.write("  .osection"+str(i) +" : AT ( _sidata  + compartLMA)\n")
				dpatch.write("  {\n")
				dpatch.write("	. = "+ str(dsections[os + str(section)][1])+";\n")
				dpatch.write("	_sosection" +str(i) +" = .;\n")
				dpatch.write("	*(.osection"+str(i)+")\n")
				dpatch.write("	. = "+ str(dsections[os + str(section)][0] + dsections[os + str(section)][1])+";\n")
				dpatch.write("	_eosection" +str(i) +" = .;\n")
				if arch=="armv7m":
					dpatch.write("  }  > RAM \n")
				else:
					dpatch.write(" }")
#				dpatch.write("  }  > RAM \n")
				dpatch.write("compartLMA = compartLMA + SIZEOF(.osection"+str(i) +"); \n")
				i += 1
	dpatch.write("_edata = .; \n")


def fixup(section):
		global fragmentation
		if section[0] == 0:
			print ("Returning empty section")
			return section[0]
		if section[0] < 32:
			fragmentation += (32 - section[0])
			section[0] = 32
		upSize = 2 ** math.ceil(Log2(section[0]))
		fragmentation += (int(upSize) - section[0])
		section[0] = int(upSize)
		if section[1] %section[0]:
				div = section[1]/section[0]
				div += 1
				print ("Update from: " + str(section[1])+ " to:"+ str(section[0] * div))
				fragmentation += ((section[0] * div) - section[1])
				section[1] = int(section[0] * div)
		print(section)
		return section[0]+section[1]
'''
def updateSize(codesections):
	it = sorted(codesections)
	for csec in sorted(codesections):
			[size,base] = codesections[csec]
			ind = it.index(csec)
			ind +=1
			if ind < len(it):
				nextSec=it[ind]
				[nsize,nbase] = codesections[nextSec]
				sizePad = nbase - base
				if not sizePad == size:
					print ("Updating size from" + str(size) + " to " + str(sizePad))
					codesections[csec][0] = sizePad
'''


def printSortedAndFixupSections(sections, start):
	totalSize = 0
	lc = start
	elemi = ''.join([i for i in list(sections.keys())[0] if not i.isdigit()])
	for elem in range(len(sections)):
		print(elemi + str(elem) + ":")
		print(sections[elemi + str(elem)])
		totalSize += sections[elemi + str(elem)][0]
		if not lc == -1: 
			sections[elemi + str(elem)][1] = lc 
		if not sections[elemi + str(elem)][0] == 0:
			valid(sections[elemi + str(elem)][1],sections[elemi + str(elem)][0])
			lc = fixup(sections[elemi + str(elem)]) #Location counter tells from where the next section base should begin.
			print(sections[elemi + str(elem)])
	return totalSize

#0-> Size
#1-> base_addr
def printSortedAndFixupSectionsData(datasections, datasections_init, start):
	totalSize = 0
	sizeObjectSection =0
	lc = start
	elemi = ''.join([i for i in list(datasections.keys())[0] if not i.isdigit()])
	for elem in range(len(datasections)):
		sizeObjectSection =0
		print(elemi + str(elem) + ":")
		print(datasections_init[elemi + str(elem) + "data"])
		print(datasections[elemi + str(elem)])
		totalSize += datasections[elemi + str(elem)][0]
		sizeObjectSection += datasections[elemi + str(elem)][0]
		totalSize += datasections_init[elemi + str(elem) + "data"][0]
		sizeObjectSection += datasections_init[elemi + str(elem) + "data"][0]
		if not lc == -1:
			datasections_init[elemi + str(elem) + "data"][1] = lc
		if not sizeObjectSection == 0:
			size = totalSize
			base = datasections_init[elemi + str(elem) + "data"][1]
			section= [size, base]
			valid(datasections_init[elemi + str(elem) + "data"][1], totalSize)
			lc = fixup(section) #Location counter tells from where the next section base should begin.
			if (section[1] > totalSize):
				pad = section[1] - datasections_init[elemi + str(elem) + "data"][0]
				datasections[elemi + str(elem)][1] = datasections[elemi + str(elem)][1] + pad
			#update base address
			datasections_init[elemi + str(elem) + "data"][1] = section[1]
			print("After fixing)")
			print(elemi + str(elem) + ":")
			print(datasections_init[elemi + str(elem) + "data"])
			print(datasections[elemi + str(elem)])
	return totalSize

def printSortedAndVerifSections(sections):
	elemi = ''.join([i for i in list(sections.keys())[0] if not i.isdigit()])
	for elem in range(len(sections)):
		 print(str(elem) + ":")
		 print(sections[elemi + str(elem)])
		 if not sections[elemi + str(elem)][0] == 0:
				valid(sections[elemi + str(elem)][1],sections[elemi + str(elem)][0])
	

def main(argv):
	global fragmentation
	global arch
	inputfile = ''
	outputfile = ''
	binary = ''
	devFile = None
	try:
		opts, args = getopt.getopt(argv,"hi:o:l:c:d:a:b:",["ifile=","ofile="])
	except getopt.GetoptError:
		print ('test.py -i <inputfile> -o <outputfile>')
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print ('test.py -i <inputfile> -o <outputfile>')
			sys.exit()
		elif opt in ("-i", "--ifile"):
			inputfile = arg
		elif opt in ("-l"):
			overlay = arg
		elif opt in ("-c"):
			configFile = arg
		elif opt in ("-d"):
			devFile = arg
		elif opt in ("-a"):
			arch = arg
		elif opt in ("-b"):
			binary = arg
	section_info = get_lma_vma_from_objdump(binary)
	outputFile = overlay.replace("overlay","ld")
	outFile = open(outputFile, "w")
	secinfo = {}
	init = []
	rtmkCode = []
	rtmkData = []
	FLASH_BASE = 0x8000000
	RAM_BASE = 0x20000000
	with open(inputfile) as f:
			lines = f.readlines()
			for line in lines:
				line = line.replace("\n","")
				
				if ".fini_array" in line:
					for word in line.split(" "):
							if word.isdigit():
									num = int(word)
									rtmkCode.append(num)
				if "._user_heap_stack" in line:
					for word in line.split(" "):
							if word.isdigit():
									num = int(word)
									rtmkData.append(num)

				if "csection" in line or "osection" in line:
					secinfo[line.split(" ")[0]] = []
					for word in line.split(" "):
							if word.isdigit():
									num = int(word)
									secinfo[line.split(" ")[0]].append(num)

	# MPU Requirements dictate that 
	#	1. size is power of 2
	#	2. size is more than 32 bytes
	#	3. base address is multiple of size.
	#
	codesections = {}
	datasections = {}
	datasections_init = {}
	for section in secinfo:
		[size, base] = secinfo[section]

		if ("csection" in section):
			codesections[section] = [size, base]
		else:
		 	if "data" in section:
		 		datasections_init[section] = [size, base]
		 	else:
			 	datasections[section] = [size, base]

	lumpText = [rtmkCode[0]+rtmkCode[1] - FLASH_BASE, FLASH_BASE]
	stat= open("./linker.stat", "w")
	fragmentation=0

	if arch=="armv7m":
		size = printSortedAndFixupSections(codesections, fixup(lumpText))
	
	codeFragmentation = fragmentation
	stat.write(str(size)+"\n")
	stat.write(str(codeFragmentation)+"\n")
	fragmentation  = 0
	lumpData = [rtmkData[0]+rtmkData[1] - RAM_BASE, RAM_BASE]
	print(lumpData)
	print("Data Init Sections")
	print(datasections_init)
	print(datasections)
	if arch=="armv7m":
		size = printSortedAndFixupSectionsData(datasections, datasections_init, fixup(lumpData))
	dataFragmentation = fragmentation
	stat.write(str(size)+"\n")
	stat.write(str(dataFragmentation)+"\n")
	

	printSortedAndVerifSections(codesections)
	
	outputFile = overlay.replace("overlay","ld")
	outFile = open(outputFile, "w")
	with open(overlay) as f:
		lines = f.readlines()
		for line in lines:
			if("datamarker-fixup::" in line):
					writeDataSections(outFile, datasections)
			elif("codemarker-fixup::" in line):
					writeCodeSections(outFile, codesections)
			else:
					outFile.write(line)
	prologue_string  = "#include <monitor.h> \n "
	if arch == "armv7m":
		prologue_string += "#include <arch/armv7m/arch.h> \n "
	prologue_string += "RTMK_DATA \n  SEC_INFO comp_info[] = {"

	if arch =="x64":
		global sizeRegionMap
		sizeRegionMap= { 0:"0", 32: "32", 64: "64", 128: "128", 256: "256", 512: "512", 1024: "1024", 2048: "2048", 4096: "4096", 8192:"8192", 16384: "16384", 32768: "32768", 65536: "65536", 131072: "131072", 262144: "262144", 524288: "524288", 1048576: "1048576", 2097152:"2097152", 4194304:"4194304",8388608:"8388608",16777216:"16777216",33554432:"33554432",67108864:"67108864",134217728:"134217728",268435456:"268435456",536870912:"536870912",1073741824:"1073741824",2147483648:"2147483648",4294967296:"4294967296"}	
	#CodeStart,CodeSize,DataStart,DataSize
	endstring = "}; \n"
	f = open(configFile, "w")
	f.write(prologue_string)
#print(datasections)
	i =0
	
	for sect in range(len(codesections)):
			section = ".csection" + str(sect)
			dsection = section 
			f.write("/*"+ section + "*/")
			dsection = ".o" + section[2:]
			#For smaller firmwares there could be compartments without any data
			if dsection in datasections:
				dsection = datasections[dsection]
			else:
				dsection = [0,0]
			csection = codesections[section]
			f.write("{")
			f.write(str(csection[1]))#Offset
			f.write(",")
#			print(section +":")
#			print(hex(int(csection[1])))
#			print(hex(int(csection[0])))

			if arch == "armv7m":
				f.write(sizeRegionMap[csection[0]])#Size
			else:
				f.write(str(csection[0]))
			f.write(",")
			f.write(str(dsection[1]))
			f.write(",")
#			print(hex(int(dsection[1])))
#			print(hex(int(dsection[0])))
			if arch == "armv7m":
				f.write(sizeRegionMap[dsection[0]])
			else:
				f.write(str(dsection[0]))
			f.write(",")
			f.write(str(csection[0] + csection[1]))
			f.write(",")
			f.write(str(dsection[0] + dsection[1]))
			[start, size, end] = [0,0,0]
			print (start)
			print(size)
			[start, size] = valid(start, size)
			end = int(start + size)
			print("After")
			print(start)
			print(size)
			if arch == "armv7m":
				f.write("," + str(start) + " , "  + sizeRegionMap[size] + " , " + str(end))
			else:
				f.write("," + str(start) + " , "  + str(size) + " , " + str(end))
			f.write("}")
			i +=1
			if i!= len(codesections):
					f.write(",")
	f.write(endstring)
	f.write("RTMK_DATA int code_base= "+ str(FLASH_BASE) + ";\n");
	if arch == "armv7m":
		f.write("RTMK_DATA int code_size= "+ str(sizeRegionMap[codesections[".csection0"][1] - FLASH_BASE]) +";\n")
	else:
		f.write("RTMK_DATA int code_size= "+ str(codesections[".csection0"][1] - FLASH_BASE) +";\n")
	f.write("RTMK_DATA int data_base= "+ str(RAM_BASE) + ";\n");
	if arch == "armv7m":
		f.write("RTMK_DATA int data_size= "+ str(sizeRegionMap[datasections[".osection0"][1] - RAM_BASE]) + ";\n")
	else:
		f.write("RTMK_DATA int data_size= "+ str(datasections[".osection0"][1] - RAM_BASE) + ";\n")


	f.write("int total_secs = sizeof(comp_info) / sizeof(comp_info[0]);")



if __name__ == "__main__":
	main(sys.argv[1:])
