import numpy as np
from labscript import *
from labscriptlib.eEDM.connection_table import ct

print("About to call ct()")
ct()
print("ct() succeeded")
start()
t = 0
photon_counter.acquire(t=2.0, number_of_counts=50_000)
# → arms for 250,000 samples total (200k skip + 50k acquire)
# → saves exactly 50,000 samples starting at t=2.0, counts normalized to 0
t += 0.5
stop(t)
print("stop() succeeded")