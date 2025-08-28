import os
import subprocess

def run(input, firmware):
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