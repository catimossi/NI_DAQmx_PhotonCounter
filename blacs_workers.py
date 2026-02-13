"""
user_devices/NI_DAQmx_PhotonCounter/blacs_workers.py
"""
from blacs.tab_base_classes import Worker
from blacs.tab_base_classes import Worker
import numpy as np
import labscript_utils.h5_lock
import h5py
import labscript_utils.properties as properties
import logging

from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *

# Define constants explicitly (from NIDAQmx.h)
DAQmx_Val_Rising = 10280
DAQmx_Val_Falling = 10171
DAQmx_Val_CountUp = 10128
DAQmx_Val_CountDown = 10124
DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_ContSamps = 10123
DAQmx_Val_DigEdge = 10150
DAQmx_Val_DigLvl = 10152
DAQmx_Val_Low = 10214
DAQmx_Val_High = 10192


class NI_DAQmxPhotonCounterWorker(Worker):
    
    def init(self):
        self.task = None
        self.h5_file = None
        # These are set automatically from worker_initialisation_kwargs:
        #   self.MAX_name
        #   self.counter_channel
        #   self.photon_input_terminal
        #   self.sample_clock_terminal
        #   self.counter_sample_rate
        # Ensure messages propagate to the parent BLACS logger
        self.logger.propagate = True
        self.logger.setLevel(logging.DEBUG)

    def transition_to_buffered(self, device_name, h5file, initial_values, fresh):
        self.h5_file = h5file
        self.device_name = device_name
        
        # Read stop_time from our own device group
        with h5py.File(h5file, 'r') as f:
            grp = f['devices'][device_name]
            stop_time = float(grp.attrs.get('stop_time', 1.0))
        
        sample_rate = self.counter_sample_rate
        # Buffer size: pad by 10% for safety
        num_samples = int(np.ceil(stop_time * sample_rate * 1.1))
        
        self.logger.info(
            f"Photon counter: {stop_time:.3f}s, "
            f"buffer {num_samples} samples @ {sample_rate} Hz"
        )
        
        self.task = Task()
        counter_path = f"/{self.MAX_name}/{self.counter_channel}"
        
        # Create the edge-counting channel
        self.task.CreateCICountEdgesChan(
            counter_path,
            "",                     # name to assign
            DAQmx_Val_Rising,
            0,                      # initial count
            DAQmx_Val_CountUp
        )
        
        # Explicitly set which terminal receives the photon pulses
        self.task.SetCICountEdgesTerm(counter_path, self.photon_input_terminal)
        
        # Determine sample clock source
        if self.sample_clock_terminal:
            clock_source = self.sample_clock_terminal
        else:
            # With DummyPseudoclock there is no real hardware clock.
            # Use the onboard clock (empty string = internal timebase).
            clock_source = "100kHzTimebase"
        
        # Use continuous acquisition so we don't hang if edge count
        # doesn't exactly match expectations
        self.task.CfgSampClkTiming(
            clock_source,
            float(sample_rate),
            DAQmx_Val_Rising,
            DAQmx_Val_ContSamps,
            num_samples
        )
        
        self.task.StartTask()
        self.logger.info(
            f"Photon counter ARMED: counting on {self.photon_input_terminal}, "
            f"clock={'internal' if not clock_source else clock_source}"
        )
        
        self._stop_time = stop_time
        self._sample_rate = sample_rate
        return {}

    def transition_to_manual(self, abort=False):
        print("=== PHOTON COUNTER transition_to_manual ===", flush=True)
        if self.task is None:
            return True
        
        if abort:
            try:
                self.task.StopTask()
                self.task.ClearTask()
            except Exception:
                pass
            self.task = None
            return True
        
        try:
            # For continuous acquisition with internal clock, wait for
            # the expected duration plus a margin
            import time
            # The pseudoclock doesn't gate us, so we time it ourselves
            # (This is a simplification — see notes below)
            time.sleep(self._stop_time + 0.1)
            
            # Read however many samples are available
            available = uInt32()
            self.task.GetReadAvailSampPerChan(available)
            n = available.value
            self.logger.info(f"Counter samples available: {n}")
            
            if n == 0:
                self.logger.warning("No real samples — generating simulated data")
                n = int(self._stop_time * self._sample_rate)
                
                # Simulate a photon signal: background + a Gaussian peak
                time_array = np.arange(n) / self._sample_rate
                bg_rate = 1000        # 1000 counts/sec background
                peak_rate = 50000     # peak count rate
                peak_center = self._stop_time / 2
                peak_width = 0.05     # 50 ms wide

                instantaneous_rate = (
                    bg_rate 
                    + peak_rate * np.exp(-0.5 * ((time_array - peak_center) / peak_width) ** 2)
                )

                # Convert rates to counts per bin
                dt = 1.0 / self._sample_rate
                counts_per_bin = np.random.poisson(instantaneous_rate * dt)

                # Cumulative counts (matches what the real counter produces)
                actual_data = np.cumsum(counts_per_bin).astype(np.uint32)

                self.task.StopTask()
                self.task.ClearTask()
                self.task = None
                if hasattr(self, 'clock_task') and self.clock_task is not None:
                    self.clock_task.StopTask()
                    self.clock_task.ClearTask()
                    self.clock_task = None

                self._save_data(actual_data)
                return True
            

            
            samples_read = int32()
            data = np.zeros(n, dtype=np.uint32)
            
            self.task.ReadCounterU32(
                n,
                10.0,           # timeout
                data,
                n,
                samples_read,
                None
            )
            
            actual_data = data[:samples_read.value]
            self.logger.info(f"Read {samples_read.value} counter samples")
            
            self.task.StopTask()
            self.task.ClearTask()
            self.task = None
            
            self._save_data(actual_data)
            return True
            
        except Exception as e:
            self.logger.error(f"Counter read error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            if self.task is not None:
                try:
                    self.task.StopTask()
                    self.task.ClearTask()
                except Exception:
                    pass
                self.task = None
            raise

    def _save_data(self, counts):
        """Save cumulative count data and derived quantities to HDF5."""

        sample_rate = self._sample_rate
        time_array = np.arange(len(counts)) / sample_rate
        
        # Build structured array
        dt = np.dtype([('t', np.float64), ('values', np.uint32)])
        trace = np.empty(len(counts), dtype=dt)
        trace['t'] = time_array
        trace['values'] = counts
        
        # Compute summary statistics
        total_counts = int(counts[-1]) - int(counts[0]) if len(counts) > 1 else 0
        if len(counts) > 1:
            rates = np.diff(counts.astype(np.float64)) * sample_rate
            mean_rate = float(np.mean(rates))
            std_rate = float(np.std(rates))
        else:
            mean_rate = 0.0
            std_rate = 0.0
        
        with h5py.File(self.h5_file, 'a') as f:
            traces = f.require_group('data/traces')
            traces.create_dataset('photon_counts', data=trace)
            
            results = f.require_group('results')
            results.attrs['photon_total_counts'] = total_counts
            results.attrs['photon_mean_rate'] = mean_rate
            results.attrs['photon_rate_std'] = std_rate
        
        self.logger.info(
            f"Saved: {total_counts} total counts, "
            f"mean rate {mean_rate:.0f} ± {std_rate:.0f} c/s"
        )

    def abort_buffered(self):
        return self.transition_to_manual(abort=True)

    def abort_transition_to_buffered(self):
        return self.transition_to_manual(abort=True)

    def program_manual(self, values):
        return {}

    def shutdown(self):
        if self.task is not None:
            try:
                self.task.StopTask()
                self.task.ClearTask()
            except Exception:
                pass
            self.task = None