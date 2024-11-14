import os
import subprocess
from sys import stderr
from tempfile import TemporaryDirectory

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class NpmRunner:
    def __init__(self, root: str) -> None:
        self.root = root

    def run(self, *args) -> None:
        subprocess.run(["npm", *args], check=True, cwd=self.root)


class FrontendBuilder(BuildHookInterface):
    def _log(self, *msg) -> None:
        prefix = f"{self.__class__.__name__}:"
        print(prefix, *msg, file=stderr)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__tempdir: TemporaryDirectory | None = TemporaryDirectory()

    def _get_config(self, name: str) -> str:
        config = self.config.get(name)
        if not config:
            raise ValueError(f"'{name}' is required in config")
        return config

    def _init_sdist(
        self, package_dir: str, version: str, build_data: dict
    ) -> None:
        npm = NpmRunner(self._get_config("node-root"))

        self._log("Checking NPM packages are up to date...")
        npm.run("ls")

        self.__tempdir = TemporaryDirectory()
        outdir = os.path.join(self.__tempdir.name, package_dir)
        os.makedirs(outdir, exist_ok=False)
        self._log(f"Building frontend to {outdir}...")
        npm.run("run", "build", "--", "--emptyOutDir", "--outDir", outdir)
        self._log(f"Built frontend to {outdir}")

        include_key = (
            "force_include_editable"
            if version == "editable"
            else "force_include"
        )
        build_data[include_key][outdir] = package_dir

    def _init_wheel(self, package_dir: str, version: str) -> None:
        if version == "editable":
            self._log("Skipping frontend build for editable package")
            return

        # Just check that the package dir exists in staging directory
        staging = self.root
        target = os.path.join(staging, package_dir)
        self._log(f"Checking that '{target}' directory exists")
        if os.path.isdir(target):
            return
        raise ValueError(
            f"No directory '{package_dir}' in staging directory '{staging}'. "
            "Try building wheel from sdist."
        )

    def initialize(self, version: str, build_data: dict) -> None:
        package_dir = self._get_config("package-dir")
        target = self.target_name
        if target == "sdist":
            self._init_sdist(package_dir, version, build_data)
        elif target == "wheel":
            self._init_wheel(package_dir, version)
        else:
            raise ValueError(f"Unsupported target: {target}")

    def finalize(self, *_) -> None:
        if self.__tempdir is not None:
            self.__tempdir.cleanup()
