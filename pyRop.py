import sys
from ast import *
from builder_base import *
from base_modules import *

cmdargs = sys.argv
if len(cmdargs) != 3:
    print("Usage: pyRop.py input_file output_file")

builder = create_builder('Test', AreaModule, LabelModule, PopModule)
builder.build(cmdargs[1])
print(builder.chain.chain)

os.makedirs(os.path.dirname(cmdargs[2]), exist_ok=True)
output_file = open(cmdargs[2], 'wb')
output_file.write(bytes(builder.chain))
output_file.close()
