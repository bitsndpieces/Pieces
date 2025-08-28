import partitioner.firmware_loader

def run(input, analysis):
    firmware = partitioner.firmware_loader.Firmware(input["firmware"], analysis)
    firmware.generate_cliques(input["firmware"])
    firmware.merge_shared_compartments()
    firmware.generate_dev_info()
    firmware.sanitize()
    firmware.write_partitions()
    firmware.dump()

    return firmware
