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
        self._stop_time = None
        self._skip_samples = 0
        self._num_samples = None

    def transition_to_buffered(self, device_name, h5file, initial_values, fresh):
        self.h5_file = h5file
        self.device_name = device_name

        with h5py.File(h5file, 'r') as f:
            grp = f['devices'][device_name]
            num_samples = int(grp.attrs['number_of_counts'])
            t_start = float(grp.attrs.get('t_start', 0.0))

        sample_rate = self.counter_sample_rate
        skip_samples = round(t_start * sample_rate)
        total_samples = skip_samples + num_samples

        self.logger.info(
            f"Photon counter: {skip_samples} skip + {num_samples} acquire = "
            f"{total_samples} total samples @ {sample_rate} Hz "
            f"(t_start={t_start:.3f}s, duration={num_samples / sample_rate:.3f}s)"
        )

        # 1. Create the task
        self.task = Task()
        counter_path = f"/{self.MAX_name}/{self.counter_channel}"

        # 2. Create the edge-counting channel
        self.task.CreateCICountEdgesChan(
            counter_path,
            "",
            DAQmx_Val_Rising,
            0,
            DAQmx_Val_CountUp
        )

        # 3. Set photon input terminal
        self.task.SetCICountEdgesTerm(counter_path, self.photon_input_terminal)

        # 4. Configure sample clock
        clock_source = (
            self.sample_clock_terminal
            if self.sample_clock_terminal
            else f"/{self.MAX_name}/100kHzTimebase"
        )
        self.task.CfgSampClkTiming(
            clock_source,
            sample_rate,
            DAQmx_Val_Rising,
            DAQmx_Val_FiniteSamps,
            total_samples
        )

        # 5. Configure arm-start trigger (CI tasks require ArmStartTrigger, not StartTrigger)
        if self.start_trigger_terminal:
            self.task.SetArmStartTrigType(DAQmx_Val_DigEdge)
            self.task.SetDigEdgeArmStartTrigSrc(self.start_trigger_terminal)
            self.task.SetDigEdgeArmStartTrigEdge(DAQmx_Val_Rising)

        # 6. Start (arm) the task — waits for start trigger before counting begins
        self.task.StartTask()
        self.logger.info(
            f"Photon counter ARMED: counting on {self.photon_input_terminal}, "
            f"clock={clock_source}, start_trigger={self.start_trigger_terminal or 'none'}"
        )

        self._skip_samples = skip_samples
        self._num_samples = num_samples
        self._stop_time = total_samples / sample_rate
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
            timeout = self._stop_time * 2.0 + 5.0  # generous timeout
            self.task.WaitUntilTaskDone(timeout)

            # available = uInt32()
            # self.task.GetReadAvailSampPerChan(available)
            # n = available.value
            # self.logger.info(f"Counter samples available: {n}")  

            # Read however many samples are available
            available = uInt32()
            self.task.GetReadAvailSampPerChan(available)
            n = available.value
            self.logger.info(f"Counter samples available: {n}")
            
            if n == 0: #simulated data
                self.logger.warning("No real samples — generating simulated data")
                total_n = int(self._stop_time * self._sample_rate)
                
                # Simulate a photon signal: background + a Gaussian peak
                # Generate over the full (skip + acquire) window
                time_array = np.arange(total_n) / self._sample_rate
                bg_rate = 1000        # 1000 counts/sec background
                peak_rate = 50000     # peak count rate
                # Peak is centred within the acquire window, not the full window
                acquire_center = (self._skip_samples + self._num_samples / 2) / self._sample_rate
                peak_width = 0.05     # 50 ms wide

                instantaneous_rate = (
                    bg_rate 
                    + peak_rate * np.exp(-0.5 * ((time_array - acquire_center) / peak_width) ** 2)
                )

                # Convert rates to counts per bin
                dt = 1.0 / self._sample_rate
                counts_per_bin = np.random.poisson(instantaneous_rate * dt)

                # Cumulative counts (matches what the real counter produces)
                cumulative = np.cumsum(counts_per_bin).astype(np.uint32)

                # Slice the acquire window and normalize to start at 0
                windowed = cumulative[self._skip_samples : self._skip_samples + self._num_samples]
                actual_data = (windowed.astype(np.int64) - int(windowed[0])).astype(np.uint32)

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
            
            raw = data[:samples_read.value]
            # Slice the acquire window and normalize cumulative counts to start at 0
            windowed = raw[self._skip_samples : self._skip_samples + self._num_samples]
            actual_data = (windowed.astype(np.int64) - int(windowed[0])).astype(np.uint32)
            self.logger.info(
                f"Read {samples_read.value} total samples; "
                f"kept {len(actual_data)} after skipping {self._skip_samples} samples"
            )
            
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
        #TODO: maybe more useful to compute mininmum and maximum count rates instead of mean/std, since the rate is not constant?
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