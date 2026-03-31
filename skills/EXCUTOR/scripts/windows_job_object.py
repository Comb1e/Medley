"""
windows_job_object.py — Wrap a subprocess in a Windows Job Object for hard resource limits.

Why: Python's `resource` module is Unix-only. On Windows, Job Objects are the
native mechanism to impose hard memory caps and to guarantee child-process cleanup.

Usage (Windows only):
    from windows_job_object import assign_to_job_object, create_limited_job
    job = create_limited_job(max_memory_mb=256)
    assign_to_job_object(job, proc.pid)
    # When `job` is garbage-collected the handle is closed.
    # All processes in the job are terminated automatically if
    # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE is set (which we do).
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Only available on Windows
if sys.platform != "win32":
    def create_limited_job(max_memory_mb: int = 256):  # noqa: D401
        """No-op on non-Windows platforms."""
        return None

    def assign_to_job_object(job, pid: int) -> None:  # noqa: D401
        """No-op on non-Windows platforms."""
        return
else:
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    # ── Win32 constants ───────────────────────
    PROCESS_ALL_ACCESS = 0x1F0FFF
    JobObjectBasicLimitInformation = 2
    JobObjectExtendedLimitInformation = 9

    JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
    JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x00000400

    # ── Structures ────────────────────────────
    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.wintypes.DWORD),
            ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
            ("PriorityClass", ctypes.wintypes.DWORD),
            ("SchedulingClass", ctypes.wintypes.DWORD),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    def create_limited_job(max_memory_mb: int = 256) -> Optional[ctypes.wintypes.HANDLE]:
        """
        Create a Windows Job Object that:
        - Caps per-process virtual memory to `max_memory_mb` MB
        - Kills all contained processes when the handle is closed (KILL_ON_JOB_CLOSE)
        Returns the Job HANDLE, or None on failure.
        """
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            logger.warning("CreateJobObjectW failed: %s", ctypes.GetLastError())
            return None

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = (
            JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | JOB_OBJECT_LIMIT_JOB_MEMORY
            | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        info.ProcessMemoryLimit = max_memory_mb * 1024 * 1024
        info.JobMemoryLimit = max_memory_mb * 1024 * 1024

        ok = kernel32.SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not ok:
            logger.warning("SetInformationJobObject failed: %s", ctypes.GetLastError())
            kernel32.CloseHandle(job)
            return None

        return job

    def assign_to_job_object(job: ctypes.wintypes.HANDLE, pid: int) -> None:
        """Assign process `pid` to `job`. Call immediately after Popen()."""
        if job is None:
            return
        proc_handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not proc_handle:
            logger.warning("OpenProcess failed for PID %s: %s", pid, ctypes.GetLastError())
            return
        try:
            ok = kernel32.AssignProcessToJobObject(job, proc_handle)
            if not ok:
                logger.warning(
                    "AssignProcessToJobObject failed for PID %s: %s",
                    pid, ctypes.GetLastError()
                )
        finally:
            kernel32.CloseHandle(proc_handle)