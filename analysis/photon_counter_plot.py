import lyse
from lyse import Run
import matplotlib.pyplot as plt
import numpy as np
import h5py

run = Run(lyse.path)

with h5py.File(run.h5_path, 'r') as f:
    trace = f['data/traces/photon_counts'][:]

time_s = trace['t']
cumulative = trace['values'].astype(np.float64)

counts_per_bin = np.diff(cumulative)
time_ms = time_s[1:] * 1e3

sample_rate = 1.0 / np.mean(np.diff(time_s))

# Rebin to 1 ms
bin_factor = int(sample_rate / 1000)
n_bins = len(counts_per_bin) // bin_factor * bin_factor
rebinned_counts = counts_per_bin[:n_bins].reshape(-1, bin_factor).sum(axis=1)
rebinned_time = time_ms[:n_bins].reshape(-1, bin_factor).mean(axis=1)

# Use lyse's figure manager — get figure by number
fig = plt.figure(1)
fig.clf()  # clear previous plot

ax1, ax2 = fig.subplots(2, 1, sharex=True)

ax1.plot(rebinned_time, rebinned_counts)
ax1.set_ylabel('Counts per ms')
ax1.set_title('Photon Counts vs Time')

ax2.plot(rebinned_time, rebinned_counts * 1000)
ax2.set_ylabel('Count rate (counts/s)')
ax2.set_xlabel('Time (ms)')

fig.tight_layout()