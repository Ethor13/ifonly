from multiprocessing import Process
from collections import defaultdict
from queue import Queue
from tqdm import tqdm
import warnings

warnings.filterwarnings("ignore", message="clamping frac to range")

l_bar = "{desc}: {percentage:3.0f}%|"
r_bar = "| {n_fmt:.5}/{total_fmt} [{elapsed}<{remaining}, " "{rate_fmt}{postfix}]"
fmt = "{l_bar}{bar}" + r_bar


class Printer:
    def __init__(self, print_queue: Queue, result_queue: Queue, parameters: dict):
        self.print_queue = print_queue
        self.result_queue = result_queue
        self.parameters = parameters

    @classmethod
    def multiprocessing_printer(cls, total: int, print_queue: Queue, result_queue: Queue, description=None):
        """Central function responsible for printing messages."""
        worker_statuses = defaultdict(int)
        progress_bar = tqdm(desc=description, total=total, bar_format=fmt, smoothing=0)

        while True:
            msg = print_queue.get()  # Get a message from the queue

            if msg == "DONE":  # Sentinel to break the loop
                break

            (date, num) = msg
            if num == "DONE":
                diff = 1 - worker_statuses[date]
                worker_statuses[date] += diff
                progress_bar.update(diff)
                result_queue.put(date)
            else:
                worker_statuses[date] += num
                progress_bar.update(num)

    def __enter__(self) -> None:
        if self.parameters["parallelize"]:
            cores = self.parameters["concurrent_threads"]
            printer_description = f"Parallel Execution ({cores} cores)"
        else:
            printer_description = "Sequential Execution"

        self.print_process = Process(
            target=Printer.multiprocessing_printer,
            args=(len(self.parameters["dates"]), self.print_queue, self.result_queue, printer_description),
        )

        self.print_process.start()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.print_queue.put("DONE")
        self.print_process.join()
