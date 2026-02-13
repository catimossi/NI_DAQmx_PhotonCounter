import numpy as np
import time
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

class CCounter:
    """
    6363 counters 0-3
    CTR 0 SRC 37 (PFI 8) 
    CTR 0 GATE 3 (PFI 9) 
    CTR 0 AUX 45 (PFI 10) 
    CTR 0 OUT 2 (PFI 12) 
    CTR 0 A 37 (PFI 8) 
    CTR 0 Z 3 (PFI 9) 
    CTR 0 B 45 (PFI 10) 
    CTR 1 SRC 42 (PFI 3) 
    CTR 1 GATE 41 (PFI 4) 
    CTR 1 AUX 46 (PFI 11) 
    CTR 1 OUT 40 (PFI 13) 
    CTR 1 A 42 (PFI 3) 
    CTR 1 Z 41 (PFI 4) 
    CTR 1 B 46 (PFI 11)
    CTR 2 SRC 11 (PFI 0) 
    CTR 2 GATE 10 (PFI 1) 
    CTR 2 AUX 43 (PFI 2) 
    CTR 2 OUT 1 (PFI 14) 
    CTR 2 A 11 (PFI 0) 
    CTR 2 Z 10 (PFI 1) 
    CTR 2 B 43 (PFI 2) 
    CTR 3 SRC 6 (PFI 5) 
    CTR 3 GATE 5 (PFI 6) 
    CTR 3 AUX 38 (PFI 7) 
    CTR 3 OUT 39 (PFI 15) 
    CTR 3 A 6 (PFI 5) 
    CTR 3 Z 5 (PFI 6) 
    CTR 3 B 38 (PFI 7) 
    FREQ OUT 1 (PFI 14) 
 
    """
    def __init__(self, ctr='0', source = "100kHzTimebase", sample_rate = 100000, samples=100000,f_arm_trigger=False, f_pause_trigger=False, f_buffered=None):
        """
        Initialize counter task. Note CTR 3 (PFI 0) may be used for arm trigger.
        
        Args:
            ctr: Counter number (0-3)
            source: Sample clock source for buffered mode (default: "100kHzTimebase") or "PFI0" for external clock
            sample_rate (Hz): sample rate for buffered mode (default: 100000). Ignored if source is external clock.
            samples: Number of samples to acquire in buffered mode (default: 100000)
            f_arm_trigger: If True, use arm start trigger on PFI0 (falling edge)
            f_pause_trigger: If True, use pause trigger on PFI0 (active low)
            f_buffered: If True, force buffered mode. If False, force unbuffered.
                       If None (default), auto-detect based on other flags.
        """
        self.task = Task()
        self.device = "PXI1Slot2" #6363 counters
        self.counter_channel = f"{self.device}/ctr{ctr}"
        self.expected_samples = samples
        
        # Determine if buffered mode
        if f_buffered is not None:
            self.is_buffered = f_buffered
        else:
            # Auto-detect: buffered if arm trigger but no pause trigger
            # Unbuffered if pause trigger OR neither
            self.is_buffered = f_arm_trigger and not f_pause_trigger
        
        # Create counter edge count channel
        self.task.CreateCICountEdgesChan(
            self.counter_channel,
            "photon_counter",
            DAQmx_Val_Rising,      # Active edge
            0,                      # Initial count
            DAQmx_Val_CountUp       # Count direction
        )
        
        if f_pause_trigger:
            # Unbuffered mode with pause trigger
            self.is_buffered = False
            self.task.SetPauseTrigType(DAQmx_Val_DigLvl)
            self.task.SetDigLvlPauseTrigSrc(f"/{self.device}/PFI0")
            self.task.SetDigLvlPauseTrigWhen(DAQmx_Val_Low)
        elif self.is_buffered:
            # Buffered mode with sample clock
            self.task.CfgSampClkTiming(
                source,                     # Source
                sample_rate,                # Rate
                DAQmx_Val_Rising,           # Active edge
                DAQmx_Val_FiniteSamps,      # Sample mode
                self.expected_samples       # Samples per channel
            )
            
            if f_arm_trigger:
                # Configure arm start trigger
                self.task.SetArmStartTrigType(DAQmx_Val_DigEdge)
                self.task.SetDigEdgeArmStartTrigSrc(f"/{self.device}/PFI0")
                self.task.SetDigEdgeArmStartTrigEdge(DAQmx_Val_Falling)
        # else: unbuffered, no triggers - no additional configuration needed

    def count(self):
        """
        Read a single counter sample (unbuffered mode only).
        
        Returns:
            int: Current counter value
        """
        if self.is_buffered:
            raise ValueError(
                "Cannot use count() in buffered mode. Use count_all() instead."
            )
        
        try:
            data = uInt32()
            self.task.ReadCounterScalarU32(
                10.0,  # Timeout in seconds
                data,
                None
            )
            return data.value
        except Exception as e:
            print(f"Error reading counter: {e}")
            self.stop_counting()
            return 0

    def count_all(self, nr_samples=-1):
        """
        Read all buffered counter samples (buffered mode only).
        
        Args:
            nr_samples: Number of samples to read. -1 reads all expected samples.
            
        Returns:
            numpy.ndarray: Array of counter values
        """
        if not self.is_buffered:
            raise ValueError(
                "Cannot use count_all() in unbuffered mode. Use count() instead."
            )
        
        try:
            # If -1, read expected number of samples
            if nr_samples == -1:
                nr_samples = self.expected_samples
            
            # Wait for acquisition to complete
            timeout = (nr_samples / 100000.0) * 2.0  # 2x expected duration
            self.task.WaitUntilTaskDone(timeout)
            
            # Check available samples
            available = uInt32()
            self.task.GetReadAvailSampPerChan(available)
            print(f"Samples available: {available.value}")
            
            # Prepare array for reading
            samples_read = int32()
            data = np.zeros(nr_samples, dtype=np.uint32)
            
            # Read the samples
            self.task.ReadCounterU32(
                nr_samples,                  # Number of samples per channel
                10.0,                        # Timeout
                data,                        # Data array
                nr_samples,                  # Array size
                samples_read,                # Samples actually read
                None
            )
            
            # Return only the samples actually read
            actual_data = data[:samples_read.value]
            print(f"Read {samples_read.value} samples")
            return actual_data
            
        except Exception as e:
            print(f"Error reading buffered counter: {e}")
            
            # Try to get diagnostic info
            try:
                total_acquired = uInt32()
                self.task.GetReadTotalSampPerChanAcquired(total_acquired)
                print(f"Total samples acquired before error: {total_acquired.value}")
            except:
                pass
            
            raise

    def start_counting(self):
        """Start the counter task."""
        try:
            self.task.StartTask()
            print(f"Counter task started (Buffered: {self.is_buffered})")
        except Exception as e:
            print(f"Error starting task: {e}")
            raise

    def stop_counting(self):
        """Stop and clear the counter task."""
        try:
            self.task.StopTask()
            self.task.ClearTask()
            print("Counter task stopped and cleared")
        except Exception as e:
            print(f"Error stopping task: {e}")

    def is_task_done(self):
        """Check if task has completed."""
        try:
            is_done = bool32()
            self.task.IsTaskDone(is_done)
            return bool(is_done.value)
        except:
            return True

    def get_available_samples(self):
        """Get number of available samples in buffer."""
        try:
            available = uInt32()
            self.task.GetReadAvailSampPerChan(available)
            return available.value
        except:
            return 0

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_counting()

if __name__ == "__main__":
    # Example 1: Simple unbuffered counter
    counter = CCounter(f_buffered=False)
    counter.start_counting()
    for i in range(100):
        print(counter.count())
        time.sleep(0.01)
    counter.stop_counting()

    # Example 2: Buffered acquisition with context manager
    with CCounter(f_arm_trigger=False, f_pause_trigger=False, f_buffered=True) as counter:
        counter.start_counting()
        time.sleep(1.1)
        data = counter.count_all()
        print(f"Acquired {len(data)} samples, rate = {data[-1]} counts/sec")
        print (data.max(), data.min(), data.mean(), data.std())

    # Example 3: Check progress during acquisition
    counter = CCounter(f_buffered=True)
    counter.start_counting()
    while not counter.is_task_done():
        print(f"Available: {counter.get_available_samples()}")
        time.sleep(0.1)
    data = counter.count_all()
    counter.stop_counting()