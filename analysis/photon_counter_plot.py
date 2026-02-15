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

# Rebinned cumulative for plotting
rebinned_cumulative = cumulative[1:n_bins+1].reshape(-1, bin_factor).mean(axis=1)

# Use lyse's figure manager
fig = plt.figure(1)
fig.clf()

ax1, ax2, ax3 = fig.subplots(3, 1, sharex=False)

# Counts per ms
ax1.plot(rebinned_time, rebinned_counts)
ax1.set_ylabel('Counts per ms')
ax1.set_title('Photon Counts vs Time')

# Count rate
ax2.plot(rebinned_time, rebinned_counts * 1000)
ax2.set_ylabel('Count rate (counts/s)')
ax2.set_xlabel('Time (ms)')

# Cumulative counts (original time axis)
ax3.plot(time_s * 1e3, cumulative)
ax3.set_ylabel('Cumulative counts')
ax3.set_xlabel('Time (ms)')
ax3.set_title('Cumulative Photon Counts')

fig.tight_layout()
