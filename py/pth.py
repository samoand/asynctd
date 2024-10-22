import os
import sys
import shutil
import glob
from importlib.metadata import distributions, PackageNotFoundError
import re

def disable_package(package_name, site_packages_dir):
    print(f'package_name: {package_name}')
    print(f'site_packages_dir: {site_packages_dir}')
    try:
        distribution = next(
            d for d in
            distributions(path=[site_packages_dir])
            if d.metadata['Name'] == package_name)
        package_dir = str(distribution.locate_file(package_name))
        print(f'package_dir: {package_dir}')


        if os.path.isdir(package_dir):
            new_package_dir = os.path.join(
                os.path.dirname(package_dir), '__disabled__' + os.path.basename(package_dir))
            os.rename(package_dir, new_package_dir)
        elif os.path.isfile(package_dir):
            new_package_file = package_dir.replace(
                os.path.basename(package_dir), '__disabled__' + os.path.basename(package_dir))
            os.rename(package_dir, new_package_file)

        print(f'Disabled package "{package_name}" by renaming it.')

    except StopIteration:
        print(f'Package "{package_name}" not found in site-packages; no need to disable.')

    except PackageNotFoundError:
        print(f'Package "{package_name}" metadata not found; possibly already removed.')
    
def delete_package(package_name, site_packages_dir):
    try:
        distribution = next(
            d for d in
            distributions(path=[site_packages_dir])
            if d.metadata['Name'] == package_name)
        package_dir = str(distribution.locate_file(package_name))


        if os.path.isdir(package_dir):
            shutil.rmtree(package_dir)
        elif os.path.isfile(package_dir):
            os.remove(package_dir)
        print(f'Removed package "{package_name}" from site-packages.')

    except StopIteration:
        print(f'Package "{package_name}" not found in site-packages; '
              'no need to remove.')

    except PackageNotFoundError:
        print(f'Package "{package_name}" metadata not found; '
              'possibly already removed.')
    
def replace_env_vars(path):
    """
    Replaces environment variables in the path with their actual values.
    Supports both $VAR and ${VAR} formats.
    """
    # Pattern to match $VAR, ${VAR}, or $(VAR)
    pattern = re.compile(r'\$(\w+)|\${(\w+)}|\$\((\w+)\)')

    def replace_match(match):
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, '')

    return pattern.sub(replace_match, path)


def replace_packages_with_pth(venv_dir, local_path_file):
    site_packages_dir = None
    python_version_dirs = glob.glob(
        os.path.join(venv_dir, 'lib', 'python*', 'site-packages'))
    
    if python_version_dirs:
        site_packages_dir = python_version_dirs[0]
    else:
        print('Error: Could not locate a site-packages '
              'directory in the specified virtual environment.')
        sys.exit(1)
    
    with open(local_path_file, 'r') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            package_name, package_path = line.split(maxsplit=1)
            package_path = os.path.expandvars(package_path)
            package_path = os.path.normpath(
                replace_env_vars(os.path.expandvars(package_path)))
            # delete_package(package_name, site_packages_dir)
            disable_package(package_name, site_packages_dir)

            pth_file_path = os.path.join(
                site_packages_dir, f'{package_name}.pth')
            with open(pth_file_path, 'w') as pth_file:
                pth_file.write(package_path + '\n')

    print('Successfully installed .pth files.')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python replace_packages_with_pth.py '
              '<venv_dir> <local_path_file>')
        sys.exit(1)

    venv_dir = sys.argv[1]
    local_path_file = sys.argv[2]
    replace_packages_with_pth(venv_dir, local_path_file)
