import sys
import re
from importlib.metadata import distribution, PackageNotFoundError

from kartograf.util import check_compatibility

CHECK_MARK = "\U00002705"
CROSS_MARK = "\U0000274C"

def __print_with_format(name, version, success, error_msg=None):
    col1 = f"{name} version:"
    col2 = f"{CHECK_MARK} OK" if success else CROSS_MARK
    col3 = "" if success else f"{error_msg}"
    return print(f"{col1:25} {col2:5} ({version}) {col3}")

def __read_requirements_txt():
    with open("requirements.txt", "r") as f:
        package_versions = {}
        pattern = r"^(.*?)(>=|==)(.*)$"
        for line in f.readlines():
            match = re.match(pattern, line)
            if match:
                package_versions[match.group(1)] = match.group(3)
    return package_versions

def rpki_version():
    try:
        check_compatibility()
    except RuntimeError as e:
        print(e)

def python_version():
    min_version = (3, 10)
    sys_version = sys.version_info
    result = sys_version >= min_version
    __print_with_format(
        "Python",
        f"{sys_version.major}.{sys_version.minor}",
        result)

def installed_packages():
    required_packages = __read_requirements_txt()
    for package, min_version in required_packages.items():
        try:
            dist = distribution(package)
            result = dist.version >= min_version
            __print_with_format(package, dist.version, result)
        except PackageNotFoundError:
            __print_with_format(package, None, False, "Not Found!")


def check_all():
    rpki_version()
    python_version()
    installed_packages()

if __name__ == "__main__":
    check_all()
