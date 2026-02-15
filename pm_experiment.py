from labscript import *
from labscript_utils import import_or_reload
ct = import_or_reload('labscriptlib.eEDM.connection_table')

start()

t = 0

t = 0.01
# Do your experiment here — turn on beams, etc.
t += 1.0

stop(t)