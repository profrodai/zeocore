"""Bounded cleanup of the worker and its observed kernel/process descendants."""

import importlib
import os
import signal
import subprocess
import time
from typing import Any


class ProcessTracker:
    """Track process identity, including descendants before their parent exits."""

    def __init__(self, process: subprocess.Popen) -> None:
        self.process = process
        self.psutil = importlib.import_module("psutil")
        self.observed: dict[int, Any] = {}
        self.groups: set[int] = set()

    def observe(self) -> None:
        """Remember descendants while the worker is still alive."""
        try:
            parent = self.psutil.Process(self.process.pid)
            for child in [parent, *parent.children(recursive=True)]:
                self.observed.setdefault(child.pid, child)
                if os.name == "posix":
                    group = os.getpgid(child.pid)
                    if group != os.getpgrp():
                        self.groups.add(group)
        except self.psutil.Error, ProcessLookupError:
            return

    def _freeze(self) -> None:
        """Prevent ordinary descendants spawning during the final cleanup scan."""
        # Stop spawning before taking the final descendant snapshots. Kernels
        # own a separate session, so freezing only the worker is insufficient.
        for _ in range(3):
            self.observe()
            for group in self.groups:
                try:
                    os.killpg(group, signal.SIGSTOP)
                except ProcessLookupError:
                    pass
        self.observe()

    def worker_memory(self) -> int:
        """A polled RSS fuse; this is not an OS-enforced peak-memory limit."""
        try:
            return int(self.psutil.Process(self.process.pid).memory_info().rss)
        except self.psutil.Error:
            return 0

    def cleanup(self, timeout: float = 5) -> bool:
        """Kill known sessions and reap our worker on every exit path."""
        deadline = time.monotonic() + timeout
        self._freeze()
        for group in self.groups:
            try:
                os.killpg(group, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for process in self.observed.values():
            try:
                process.kill()
            except self.psutil.NoSuchProcess:
                pass
        self.process.kill()
        try:
            self.process.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            return False
        return self._wait_for_descendants(deadline)

    def _wait_for_descendants(self, deadline: float) -> bool:
        """Observe termination within the remaining cleanup allowance."""
        while time.monotonic() < deadline:
            alive = []
            for process in self.observed.values():
                try:
                    if (
                        process.is_running()
                        and process.status() != self.psutil.STATUS_ZOMBIE
                    ):
                        alive.append(process)
                except self.psutil.NoSuchProcess:
                    pass
            if not alive:
                return True
            time.sleep(0.01)
        return False
