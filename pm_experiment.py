import numpy as np
from labscript import *
from labscriptlib.eEDM.connection_table import ct

print("About to call ct()")
ct()
print("ct() succeeded")
print("About to call start()")
start()
print("start() succeeded")
t = 0
t = t + 1.0
stop(t)
print("stop() succeeded")