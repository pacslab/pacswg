import queue
import time
import threading
from pacswg.timer import *

import numpy as np

def get_random_wait_time(rps):
    """get_random_wait_time generates random exponential inter-arrival times corresponding to Poisson process.
    
    :param rps: rps or requests per second is the target number of requests per second
    :type rps: float
    :return: a draw from the resulting exponential distribution for inter-arrival time
    :rtype: float
    """    
    scale = 1/rps
    return np.random.exponential(scale)

class WorkerThread(threading.Thread):
    def __init__(self, parent, sleep_time=2):
        super(WorkerThread, self).__init__()
        # if daemon is true this thread will die when the main thread dies
        self.daemon = True
        self.stop_signal = False
        self.parent = parent

    def run(self):
        while not self.stop_signal:
            try:
                item = self.parent.q.get(timeout=1)
                # print('-', end='')
                if item is None:
                    time.sleep(.01)
                    continue
                else:
                    res = self.parent.worker_func()
                    self.parent.temp_stats.append(res)
            except queue.Empty:
                time.sleep(.01)
                continue

class WorkloadGenerator:
    """WorkloadGenerator is the class responsible for generating the desired workload using the delay function provided, to achieve the target requests per second.
    
    :return: an instance of the WorkloadGenerator class
    :rtype: object
    """    
    def __init__(self, worker_func, rps=10/60, delay_func=None, worker_thread_count=10, *args, **kwargs):
        """__init__ for WorkloadGenerator class.
        
        :param worker_func: the worker function that will be called by the worker threads, it shouldn't have any arguments and should return a dict.
        :type worker_func: function
        :param rps: desired requests per second to be achieved by the workload generator, defaults to 10/60
        :type rps: float, optional
        :param delay_func: the function that generates a draw from inter-arrival time given rps as an argument, defaults to exponential distribution
        :type delay_func: function, optional
        :param worker_thread_count: number of worker threads, defaults to 10
        :type worker_thread_count: int, optional
        """        
        super().__init__(*args, **kwargs)

        self.rps = rps
        self.worker_threads = None
        self.temp_stats = []
        self.worker_thread_count = worker_thread_count
        self.worker_func = worker_func
        self.q = queue.Queue()
        self.fire_timer = TimerClass()
        self.prepare_test()

        if delay_func is None:
            self.delay_func = get_random_wait_time
        else:
            self.delay_func = delay_func

    def get_stats(self):
        """get_stats gathers the values generated by calling the workload function throughout the test.
        
        :return: stats
        :rtype: array of dicts
        """        
        return self.temp_stats

    def fire(self):
        """fire causes one of the worker threads to call worker_func once
        """        
        self.q.put(1)

    def reset_stats(self):
        """reset_stats resets the info gathered from worker threads.
        
        :return: sucess
        :rtype: boolean
        """        
        self.temp_stats = []
        return True
    
    def set_rps(self, new_rps):
        """set_rps sets the number of requests per second that will be made by the workers.

        :param new_rps: the new rps
        :type new_rps: float
        :return: success
        :rtype: boolean
        """        
        if new_rps < 1/60:
            new_rps = 1/60
        self.rps = new_rps
        return True

    def prepare_test(self):
        """prepare_test resets the timer that will be used to time the requests.
        """        
        self.fire_timer.tic()

    def fire_wait(self):
        """fire_wait fires a request, generates an inter-arrival delay using delay_finc, then waits for that amount of time.
        """        
        self.fire_timer.tic()
        self.fire()
        wait_time = self.delay_func(self.rps) - self.fire_timer.toc()
        if wait_time > 0:
            time.sleep(wait_time)

    def stop_workers(self):
        """stop_workers stops all workers and waits until the threads are all shut down.
        
        :return: success
        :rtype: boolean
        """        
        if self.worker_threads is not None:
            for worker_thread in self.worker_threads:
                worker_thread.stop_signal = True
            # Wait for them to finish up
            for worker_thread in self.worker_threads:
                worker_thread.join()
            return True
        else:
            return True

    def __del__(self):
        self.stop_workers()

    def start_workers(self):
        """start_workers starts up the worker pool
        """        
        self.stop_workers()
        self.worker_threads = []
        for i in range(self.worker_thread_count):
            worker_thread = WorkerThread(self)
            worker_thread.start()
            self.worker_threads.append(worker_thread)
