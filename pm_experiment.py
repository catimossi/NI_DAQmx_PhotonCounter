import numpy as np
from labscript import *
from labscriptlib.eEDM.connection_table import ct

print("About to call ct()")
ct()
print("ct() succeeded")
start()
t = 0
# Starting at 1.0 sec, take 50000 samples at 100 kHz, which should take 0.5 seconds
photon_counter.acquire(t=1.0, number_of_counts=50_000)

t += 0.5
stop(t)
print("stop() succeeded")