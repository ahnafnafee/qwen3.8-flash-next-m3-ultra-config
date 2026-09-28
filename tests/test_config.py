import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qwen-config-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model = self.root / "Mac's model folder"
        self.bin = self.root / "command bin"
        self.env = dict(os.environ, QWEN_MODEL_DIR=str(self.model), QWEN_PORT="65003")

    def run_command(self, command, **kwargs):
        return subprocess.run(command, env=self.env, capture_output=True, text=True, **kwargs)

    def install(self, *args):
        return self.run_command([
            sys.executable, str(REPO / "install.py"), "--model-dir", str(self.model),
            "--bin-dir", str(self.bin), *args,
        ])

    def test_syntax(self):
        for path in REPO.glob("*.sh"):
            result = self.run_command(["bash", "-n", str(path)])
            self.assertEqual(result.returncode, 0, result.stderr)
        for path in REPO.glob("*.py"):
            ast.parse(path.read_text(), filename=str(path))

    def test_install_idempotence_backups_and_weight_preservation(self):
        self.model.mkdir()
        weight = self.model / "ngram_table.bin"
        weight.write_bytes(b"unchanged fixture")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.install().returncode, 0)
        start = self.model / "start.sh"
        start.write_text("# old custom management script\n")
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual(start.read_text(), "# old custom management script\n")
        self.assertEqual(self.install("--force").returncode, 0)
        backups = list((self.model / ".qwen-config-backups").glob("*/*"))
        self.assertTrue(any(p.read_text() == "# old custom management script\n" for p in backups))
        self.assertEqual(weight.read_bytes(), b"unchanged fixture")

    def test_installed_status_rejects_unrelated_pid(self):
        self.assertEqual(self.install().returncode, 0)
        state = self.model / ".service"
        state.mkdir()
        (state / "server.pid").write_text(str(os.getpid()) + "\n")
        for status in (self.bin / "qwen-status", self.model / "status.sh"):
            result = self.run_command([str(status)])
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(self.run_command([str(self.bin / "qwen-stop")]).returncode, 0)
        os.kill(os.getpid(), 0)

    def test_launcher_keeps_winning_settings_and_quoted_path(self):
        self.model.mkdir()
        (self.model / "config.json").write_text("{}")
        (self.model / "ngram_table.bin").write_bytes(b"fixture")
        fake = self.root / "mlx-serve"
        fake.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n')
        fake.chmod(0o755)
        self.env["MLX_SERVE_BIN"] = str(fake)
        self.env["QWEN_PORT"] = "11234"
        result = self.run_command([str(REPO / "serve_mlx_best.sh")])
        self.assertEqual(result.returncode, 0, result.stderr)
        args = result.stdout.splitlines()
        for flag, value in {
            "--model": str(self.model), "--host": "0.0.0.0", "--port": "11234",
            "--ctx-size": "262144", "--mtp-depth": "3", "--kv-quant": "8",
            "--kv-attn-mode": "fused", "--prefix-cache-mem": "16GB",
        }.items():
            self.assertEqual(args[args.index(flag) + 1], value)
        for flag in ("--mtp", "--no-pld", "--no-vision", "--metrics"):
            self.assertIn(flag, args)

    def test_hf_commands_are_pinned(self):
        self.bin.mkdir()
        fake = self.bin / "hf"
        fake.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n')
        fake.chmod(0o755)
        self.env["PATH"] = str(self.bin) + os.pathsep + os.environ["PATH"]
        for script in ("download-model.sh", "verify-model.sh"):
            result = self.run_command([str(REPO / script)])
            self.assertEqual(result.returncode, 0, result.stderr)
            args = result.stdout.splitlines()
            self.assertEqual(args[args.index("--revision") + 1], "9ebf9993b1eaec96aec938bf883601b51a90393b")
            self.assertEqual(args[args.index("--local-dir") + 1], str(self.model))
        self.assertIn("--fail-on-missing-files", args)

    def test_installer_refuses_symlink_target(self):
        self.model.mkdir()
        unrelated = self.root / "unrelated.txt"
        unrelated.write_text("preserve me")
        (self.model / "start.sh").symlink_to(unrelated)
        self.assertNotEqual(self.install("--force").returncode, 0)
        self.assertEqual(unrelated.read_text(), "preserve me")


if __name__ == "__main__":
    unittest.main()
