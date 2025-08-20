opt -enable-new-pm=0 -dot-callgraph -disable-output /stm324/build/RTOSDemo.axf.bc
cp /stm324/build/RTOSDemo.axf.bc.callgraph.dot ./light-cg.dot
rm /stm324/build/RTOSDemo.axf.bc.callgraph.dot

~/SVF/Release-build/bin/use-def-light /stm324/build/RTOSDemo.axf.bc /pieces/analyzer/light-dg.dot

python3 gen_pdg.py ./light-dg.dot ./light-cg.dot
