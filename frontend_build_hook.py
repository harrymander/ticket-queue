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
        self.__tempdir: TemporaryDirectory = TemporaryDirectory()

    def _get_config(self, name: str) -> str:
        config = self.config.get(name)
        if not config:
            raise ValueError(f"'{name}' is required in config")
        return config

    def _build_frontend(
        self,
        config: Config,
        version: str,
        build_data: dict,
    ) -> None:
        workdir = self.__tempdir.name
        npm = NpmRunner(config.node_root)

        self._log("Installing NPM packages...")
        npm.run("install")

        outdir = os.path.join(workdir, config.package_dir)
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

        package_module = os.path.join(workdir, config.package_module)
        relpath = os.path.relpath(
            config.package_dir, os.path.dirname(config.package_module)
        )
        with open(package_module, "w") as f:
            f.write(_MODULE_TEMPLATE.format(package_dir=relpath))

        build_data[include_key][package_module] = config.package_module

    def _wheel_path_exists(self, path: str, *, is_dir: bool = False) -> bool:
        check = os.path.isdir if is_dir else os.path.exists
        return check(os.path.join(self.root, path))

    def _wheel_needs_frontend(self, config: Config, version: str) -> bool:
        if version == "editable":
            self._log("Skipping frontend build for editable package")
            return False

        wheel_exists = self._wheel_path_exists(
            config.package_module
        ) and self._wheel_path_exists(config.package_dir, is_dir=True)
        if wheel_exists:
            self._log("Building wheel from sdist, not re-building frontend")
        return not wheel_exists

    def initialize(self, version: str, build_data: dict) -> None:
        config = Config.from_config(self.config)

        target = self.target_name
        if target == "sdist":
            build_frontend = True
        elif target == "wheel":
            build_frontend = self._wheel_needs_frontend(config, version)
        else:
            raise ValueError(f"Unsupported target: {target}")

        if build_frontend:
            self._build_frontend(
                config,
                version,
                build_data,
            )

    def finalize(self, *_) -> None:
        self.__tempdir.cleanup()
