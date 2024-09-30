import sys
import os
import re
from kartograf.util import check_compatibility
from pathlib import PurePath
from importlib.metadata import distribution

CHECK_MARK = "\U00002705"
CROSS_MARK = "\U0000274C"

def __print_with_format(name, version, success, error_msg=None):
    col1 = f"{name} version:"
    col2 = f"{CHECK_MARK} OK" if success else CROSS_MARK
    col3 = "" if success else f"{error_msg}"
    return print(f"{col1:25} {col2:5} ({version}) {col3}")

def __read_requirements_txt():
    with open("requirements.txt", "r") as f:
        package_versions = dict()
        pattern = r"^(.*?)(>=|==)(.*)$"
        for line in f.readlines():
            match = re.match(pattern, line)
            if match:
                package_versions[match.group(1)] = match.group(3)
    return package_versions

def test_rpki_version():
    check_compatibility()

def test_python_version():
    min_version = (3, 10)
    sys_version = sys.version_info
    result = (sys_version >= min_version)
    __print_with_format(
        "Python",
        f"{sys_version.major}.{sys_version.minor}",
        result)
    assert result

def test_installed_packages():
    python_executable_path = PurePath(sys.executable)
    python_env_path = python_executable_path.parents[1].as_posix()
    required_packages = __read_requirements_txt()
    for package, min_version in required_packages.items():
        dist = distribution(package)
        # assert that our package versions meet requirements
        assert dist.version >= min_version
        # assert that our python packages are in the python env (the project Nix store path)
        common_path = os.path.commonpath(
            [dist.locate_file('.'), python_executable_path])
        result = (common_path == python_env_path)
        __print_with_format(package, dist.version, result)
        assert result
