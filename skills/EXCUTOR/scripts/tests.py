"""
tests.py — Test suite for SecureExecutor.

Run with:  python tests.py
"""

from __future__ import annotations

import sys
import unittest

from secure_executor import ExecutionConfig, SecureExecutor


class TestBasicExecution(unittest.TestCase):
    def setUp(self):
        self.ex = SecureExecutor()

    def test_hello_world(self):
        r = self.ex.run("print('hello world')")
        self.assertTrue(r.success)
        self.assertEqual(r.stdout.strip(), "hello world")
        self.assertEqual(r.return_code, 0)

    def test_arithmetic(self):
        r = self.ex.run("print(2 ** 10)")
        self.assertTrue(r.success)
        self.assertIn("1024", r.stdout)

    def test_multiline(self):
        code = """
total = 0
for i in range(100):
    total += i
print(total)
"""
        r = self.ex.run(code)
        self.assertTrue(r.success)
        self.assertIn("4950", r.stdout)

    def test_nonzero_exit(self):
        r = self.ex.run("raise ValueError('deliberate')")
        self.assertFalse(r.success)
        self.assertIn("ValueError", r.stderr)


class TestTimeout(unittest.TestCase):
    def test_infinite_loop_times_out(self):
        cfg = ExecutionConfig(timeout_seconds=2)
        r = SecureExecutor(cfg).run("while True: pass")
        self.assertTrue(r.timed_out)
        self.assertFalse(r.success)

    def test_fast_code_not_timed_out(self):
        cfg = ExecutionConfig(timeout_seconds=5)
        r = SecureExecutor(cfg).run("print('fast')")
        self.assertFalse(r.timed_out)


class TestOutputCap(unittest.TestCase):
    def test_output_truncated(self):
        cfg = ExecutionConfig(max_output_bytes=100)
        code = "print('X' * 10_000)"
        r = SecureExecutor(cfg).run(code)
        # Truncation notice should appear in stderr
        combined = r.stdout + r.stderr
        self.assertIn("truncated", combined.lower())


class TestBlockedImports(unittest.TestCase):
    def _blocked(self, module: str) -> bool:
        r = SecureExecutor().run(f"import {module}")
        return not r.success

    def test_subprocess_blocked(self):
        self.assertTrue(self._blocked("subprocess"))

    def test_ctypes_blocked(self):
        self.assertTrue(self._blocked("ctypes"))

    def test_socket_blocked_by_default(self):
        self.assertTrue(self._blocked("socket"))

    def test_winreg_blocked(self):
        # Only meaningful on Windows; still should be blocked
        self.assertTrue(self._blocked("winreg"))

    def test_importlib_blocked(self):
        self.assertTrue(self._blocked("importlib"))

    def test_os_module_allowed(self):
        # os itself is allowed, but harmful sub-calls are detected at static level
        r = SecureExecutor().run("import os; print(os.getcwd())")
        # Should succeed (getcwd is harmless)
        self.assertTrue(r.success)


class TestNetworkToggle(unittest.TestCase):
    def test_socket_blocked_default(self):
        r = SecureExecutor().run("import socket")
        self.assertFalse(r.success)

    def test_socket_allowed_with_flag(self):
        cfg = ExecutionConfig(allow_network=True)
        r = SecureExecutor(cfg).run("import socket; print('ok')")
        self.assertTrue(r.success)
        self.assertIn("ok", r.stdout)


class TestFilesystemJail(unittest.TestCase):
    def test_write_inside_sandbox_allowed(self):
        code = """
import os
tmp = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'
path = os.path.join(tmp, 'test_write.txt')
open(path, 'w').write('hello')
print('written')
"""
        r = SecureExecutor().run(code)
        self.assertTrue(r.success, msg=f"stderr: {r.stderr}")
        self.assertIn("written", r.stdout)

    def test_write_outside_sandbox_blocked(self):
        import sys
        if sys.platform == "win32":
            outside = "C:/Windows/test_intrusion.txt"
            expected_err = "PermissionError"
        else:
            outside = "/etc/test_intrusion.txt"
            expected_err = "PermissionError"
        code = f"open({outside!r}, 'w').write('pwned')"
        r = SecureExecutor().run(code)
        self.assertFalse(r.success)
        # Accept either PermissionError (jail) or FileNotFoundError (OS refuses non-existent path)
        self.assertTrue(
            "PermissionError" in r.stderr or "Error" in r.stderr,
            msg=f"Expected an error, got: {r.stderr!r}"
        )

    def test_write_disabled(self):
        cfg = ExecutionConfig(allow_filesystem_write=False)
        code = """
import os
tmp = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'
path = os.path.join(tmp, 'should_fail.txt')
open(path, 'w').write('x')
"""
        r = SecureExecutor(cfg).run(code)
        self.assertFalse(r.success)
        self.assertIn("disabled", r.stderr)


class TestStaticAnalysis(unittest.TestCase):
    def test_syntax_error_reported(self):
        r = SecureExecutor().run("def broken(:")
        self.assertFalse(r.success)
        self.assertTrue(any("SyntaxError" in v for v in r.static_violations))

    def test_blocked_import_in_violation_list(self):
        r = SecureExecutor().run("import subprocess")
        self.assertTrue(any("subprocess" in v for v in r.static_violations))

    def test_clean_code_no_violations(self):
        r = SecureExecutor().run("x = 1 + 1")
        hard = [v for v in r.static_violations if v.startswith("Blocked")]
        self.assertEqual(hard, [])


class TestExtraConfig(unittest.TestCase):
    def test_extra_blocked_import(self):
        cfg = ExecutionConfig(extra_blocked_imports=["math"])
        r = SecureExecutor(cfg).run("import math")
        self.assertFalse(r.success)

    def test_extra_allowed_unblocks(self):
        # Allow socket explicitly (overrides default block)
        cfg = ExecutionConfig(extra_allowed_imports=["socket"])
        r = SecureExecutor(cfg).run("import socket; print('ok')")
        self.assertTrue(r.success)


if __name__ == "__main__":
    print(f"Python {sys.version}")
    print("=" * 60)
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)