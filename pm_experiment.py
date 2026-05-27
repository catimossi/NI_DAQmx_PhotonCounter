import numpy as np
from labscript import *
from labscriptlib.eEDM.connection_table import ct

print("About to call ct()")
ct()
print("ct() succeeded")
start()
t = 0
ct.photon_counter.acquire(t, 50_000)   # 500 ms at 100 kHz
# or: photon_counter.start(50_000)
t += 0.5
stop(t)
print("stop() succeeded")