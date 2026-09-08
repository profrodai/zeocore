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

    def cleanup(self) -> bool:
        """Kill known sessions and reap our worker on every exit path."""
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
        self.process.wait(timeout=10)
        deadline = time.monotonic() + 5
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
