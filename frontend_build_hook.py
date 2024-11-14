import os
import subprocess
from dataclasses import dataclass
from sys import stderr
from tempfile import TemporaryDirectory

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class NpmRunner:
    def __init__(self, root: str) -> None:
        self.root = root

    def run(self, *args) -> None:
        subprocess.run(["npm", *args], check=True, cwd=self.root)


@dataclass
class Config:
    package_module: str
    package_dir: str
    node_root: str

    @classmethod
    def from_config(cls, config: dict) -> "Config":
        kw = {}
        for key in cls.__dataclass_fields__.keys():
            config_key = key.replace("_", "-")
            val = config.get(config_key)
            if val is None:
                raise ValueError(f"'{config_key}' is required in config")
            kw[key] = val

        return cls(**kw)


_MODULE_TEMPLATE = """\
import os.path

PACKAGE_DIR = os.path.join(
    os.path.dirname(__file__),
    {package_dir!r}
)
"""


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
        self, config: Config, version: str, build_data: dict
    ) -> None:
        npm = NpmRunner(self._get_config("node-root"))

        self._log("Checking NPM packages are up to date...")
        npm.run("ls")

        self.__tempdir = TemporaryDirectory()
        tempdir = self.__tempdir.name
        outdir = os.path.join(tempdir, config.package_dir)
        os.makedirs(outdir, exist_ok=False)
        self._log(f"Building frontend to {outdir}...")
        npm.run("run", "build", "--", "--emptyOutDir", "--outDir", outdir)
        self._log(f"Built frontend to {outdir}")

        include_key = (
            "force_include_editable"
            if version == "editable"
            else "force_include"
        )
        build_data[include_key][outdir] = config.package_dir

        package_module = os.path.join(tempdir, config.package_module)
        relpath = os.path.relpath(
            config.package_dir, os.path.dirname(config.package_module)
        )
        with open(package_module, "w") as f:
            f.write(_MODULE_TEMPLATE.format(package_dir=relpath))

        build_data[include_key][package_module] = config.package_module

    def _check_wheel_path(self, path: str, *, is_dir: bool = False) -> None:
        staging = self.root
        check = os.path.isdir if is_dir else os.path.exists
        if check(os.path.join(staging, path)):
            return

        ptype = "directory" if is_dir else "path"
        raise ValueError(
            f"No {ptype} '{path}' in staging directory '{staging}. "
            "Try building wheel from sdist."
        )

    def _init_wheel(self, config: Config, version: str) -> None:
        if version == "editable":
            self._log("Skipping frontend build for editable package")
            return

        # Just check that the generated files have been created
        self._check_wheel_path(config.package_module)
        self._check_wheel_path(config.package_dir, is_dir=True)

    def initialize(self, version: str, build_data: dict) -> None:
        config = Config.from_config(self.config)
        target = self.target_name
        if target == "sdist":
            self._init_sdist(config, version, build_data)
        elif target == "wheel":
            self._init_wheel(config, version)
        else:
            raise ValueError(f"Unsupported target: {target}")

    def finalize(self, *_) -> None:
        if self.__tempdir is not None:
            self.__tempdir.cleanup()
