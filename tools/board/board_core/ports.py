"""Output ports and the errors they may raise. No infrastructure imports."""
from typing import Protocol


class VersionConflict(Exception):
    """expected_version does not match the stored version (INV-BL-5)."""


class NotFound(Exception):
    """No task with that id."""


class AlreadyExists(Exception):
    """Create with an id that already exists (INV-BL-5)."""


class LockTimeout(Exception):
    """Could not acquire the store lock in time (INV-BL-8, T-BL-5)."""


class StoreCorrupt(Exception):
    """The data file cannot be parsed; writes are refused (INV-BL-8)."""


class ITaskStore(Protocol):
    def load(self):
        """Return all tasks sorted by id."""

    def get(self, task_id):
        """Return one task or raise NotFound."""

    def create(self, task):
        """Insert a new task (version 1); raise AlreadyExists if the id is taken."""

    def update(self, task_id, expected_version, mutate):
        """Atomically: read current task, check version, store mutate(current) with version + 1."""

    def remove(self, task_id):
        """Delete one task or raise NotFound."""


class IReleaseStore(Protocol):
    def load(self):
        """Return all releases."""


class LaunchError(Exception):
    """The agent CLI could not be started (missing executable, unsafe argv, OS error)."""


class IDispatchStateStore(Protocol):
    def load(self):
        """Return the dispatch state document (a default idle state when none exists)."""

    def update(self, mutate):
        """Atomically: read state, store mutate(state), return the stored state."""


class IRunHandle(Protocol):
    pid: int

    def poll(self):
        """Exit code, or None while running."""

    def terminate_tree(self):
        """Kill the process and all of its children."""

    def read_output(self):
        """stdout + stderr captured so far, as text."""

    def close(self):
        """Release log file handles."""


class IAgentLauncher(Protocol):
    def launch(self, argv, cwd, env, prompt_text, prompt_via, log_dir):
        """Start one agent process (no shell); write prompt/logs under log_dir; raise LaunchError."""


class IClock(Protocol):
    def time(self):
        """Seconds since the epoch (float)."""

    def now_iso(self):
        """Local ISO-8601 timestamp with offset, seconds precision."""
