#!/usr/bin/python3

import sys, getopt

def writeCodeSections(cpatch, num):
	print("Number of compartments:" +str(num))
	#Write prefix
	cpatch.write(f"CODE_SECTIONS_START = LOADADDR(.osection{num-1}data) + SIZEOF(.osection{num-1}data);\n")
	cpatch.write(f"COMPARTMENT_CODE_COUNTER = 0;\n")
	for i in range(num):
			cpatch.write("  .csection"+str(i) + " (CODE_SECTIONS_START + COMPARTMENT_CODE_COUNTER) : AT(CODE_SECTIONS_START + COMPARTMENT_CODE_COUNTER)\n")
			cpatch.write("  {\n")
			cpatch.write("_scsection"+str(i)+" = .;\n")
			cpatch.write("	  . = ALIGN(4);\n")
			cpatch.write("	  *(.csection"+str(i)+")\n")
			cpatch.write("	  . = ALIGN(4);\n")
			cpatch.write("_ecsection"+str(i)+" = .;\n")
			cpatch.write("_szcsection"+str(i)+" = _ecsection" +str(i) +" - _scsection" +str(i) +";")
			cpatch.write("  } > FLASH \n")
			cpatch.write(f"COMPARTMENT_CODE_COUNTER = COMPARTMENT_CODE_COUNTER + SIZEOF(.csection{i}); \n")

def writeDataSections(dpatch, num):
	#Write prefix
	dpatch.write(f"COMPARTMENT_DATA_START = LOADADDR(.data) + SIZEOF(.data); \n")
	dpatch.write(f"COMPARTMENT_DATA_COUNTER = 0;\n")
	for i in range(num):
			dpatch.write("  .osection"+str(i) +"data : AT (COMPARTMENT_DATA_START + COMPARTMENT_DATA_COUNTER) \n")
			dpatch.write("  { . = ALIGN(4); \n")
			dpatch.write("		_sosection"+str(i) +"data = .; \n")
			dpatch.write("  *(.osection" +str(i)+"data)		   /* .data sections. */\n")
			dpatch.write("  . = ALIGN(4); \n")
			dpatch.write("  _eosection"+str(i) + "data = .;\n")
			dpatch.write("} > RAM \n")
			dpatch.write(f"COMPARTMENT_DATA_COUNTER = COMPARTMENT_DATA_COUNTER + SIZEOF(.osection{i}data); \n")
			dpatch.write("_sosection" +str(i)+"datal = LOADADDR(.osection" +str(i)+"data);\n")
			dpatch.write("  .osection"+str(i) +" :\n")
			dpatch.write("  {\n")
			dpatch.write("	  . = ALIGN(4);\n")
			dpatch.write("	  _sosection" +str(i) +" = .;\n")
			dpatch.write("	  *(.osection"+str(i)+")\n")
			dpatch.write("	  . = ALIGN(4);\n")
			dpatch.write("	  _eosection" +str(i) +" = .;\n")
			dpatch.write("_szosection" +str(i) +" = _eosection" +str(i) +" - _sosection" +str(i) +"data;")
			dpatch.write("  }  > RAM \n")

def main(argv):
	num = 0
	heapConfig = ""
	arch = "armv7m"
	try:
		opts, args = getopt.getopt(argv,"hn:l:o:c:H:a:")
	except getopt.GetoptError:
		print("test.py -i <inputfile> -o <outputfile>")
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print("test.py -i <inputfile> -o <outputfile>")
			sys.exit()
		elif opt in ("-n"):
			print(arg)
			num = int(arg)
		elif opt in ("-l"):
			overlay = arg
		elif opt in ("-c"):
			configFile = arg
		elif opt in ("-H"):
			heapConfig = arg
		elif opt in ("-a"):
			arch = arg

	outputFile = overlay.replace("overlay","ld")
	outFile = open(outputFile, "w")
	with open(overlay) as f:
		lines = f.readlines()
		for line in lines:
			if("datamarker-fixup::" in line):
					writeDataSections(outFile, num)
			elif("codemarker-fixup::" in line):
					writeCodeSections(outFile, num)
			else:
					outFile.write(line)

	prologue_string  = "#include <monitor.h> \n"
	#CodeStart,CodeSize,DataStart,DataSize
	endstring = "};\n"
	f = open(configFile, "w")
	f.write(prologue_string)
	for i in range(num):
			f.write("LINKER_SYM(" +str(i) +");\n")

	f.write("PRIVILEGED_DATA SEC_INFO comp_info[] = {")
	for i in range(num):
			f.write("{(int)&_scsection" +str(i) +",(int) &_szcsection" +str(i) +",(int) &_sosection" +str(i) +"data, (int) &_szosection" +str(i) +", 0,0,0,0,0}" ) 
			if i!= (num -1):
					f.write(",\n")
	f.write(endstring)
	f.write("PRIVILEGED_DATA unsigned long section_loads[] = {\n") 

	for i in range(num):
		f.write("(long)&_sosection" +str(i) +"datal")
		if i!= (num -1):
					f.write(",\n")

	f.write(endstring)

	f.write("PRIVILEGED_DATA unsigned long end_loads[] = {\n") 

	for i in range(num):
		f.write("(long)&_eosection" +str(i) +"data")
		if i!= (num -1):
					f.write(",\n")

	f.write(endstring)

	f.write("PRIVILEGED_DATA int code_base;")
	f.write("PRIVILEGED_DATA int code_size;")
	f.write("PRIVILEGED_DATA int data_base;")
	f.write("PRIVILEGED_DATA int data_size;")

	f.write("PRIVILEGED_DATA int total_secs = sizeof(comp_info) / sizeof(comp_info[0]);")

	if not heapConfig:
		return
	ha={}
#	with open("./rtmk.ha") as f:
#		lines = f.readlines()
#		for line in lines:
#			[comp, use] = line.split(":")
#			ha[comp] = use
			
	f = open(heapConfig, "w")
	#Find all users so we divide accordingly
	users = 0

#See how many compartments use dynamic memory
	for i in range(num):
			if str(i) in ha:
					users = users + 1
	for i in range(num):
			if str(i) in ha:
				f.write("__attribute__((section(\".osection"+ str(i)+"\"))) uint8_t ucHeap"+ str(i)+"[ configTOTAL_HEAP_SIZE/"+str(users) +"]; \n")

	f.write("uint8_t* ucHeap[] = {")
	for i in range(num):
			if str(i) in ha:
				f.write("ucHeap"+ str(i))
			else:
				f.write("NULL")
			if not i== num-1:
				f.write(",")
	f.write("}; \n")

	f.write("uint8_t ucHeapInitFlag["+str(num)+"]; \n")
	f.write("size_t xNextFreeByte ["+str(num)+"]; \n")
	f.write("size_t heapSize ["+str(num)+"] = {")
	for i in range(num):
#			if str(i) in ha:
#				f.write("configTOTAL_HEAP_SIZE/"+str(users))
#				if not i == num-1:
#					f.write(",")
#			else:
				f.write("0")
				if not i == num-1:
					f.write(",")
	f.write("}; \n");

				


	

if __name__ == "__main__":
	main(sys.argv[1:])
