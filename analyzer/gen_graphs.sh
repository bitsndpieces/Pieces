svf-ex /stm324/build/RTOSDemo.axf.bc  -dump-vfg -dump-icfg
python3 gen_pdg.py ./svfg_final.dot ./icfg_initial.dot
