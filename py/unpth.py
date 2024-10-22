import os
import sys
import shutil
import glob
from importlib.metadata import distributions, PackageNotFoundError
import re

def enable_package(package_name, site_packages_dir):
    disabled_prefix = '__disabled__'
    
    try:
        disabled_package_dir = os.path.join(
            site_packages_dir, f'{disabled_prefix}{package_name}')

        if os.path.isdir(disabled_package_dir):
            enabled_package_dir = os.path.join(
                os.path.dirname(disabled_package_dir), package_name)
            os.rename(disabled_package_dir, enabled_package_dir)
        elif os.path.isfile(disabled_package_dir):
            enabled_package_file = disabled_package_dir.replace(
                f'{disabled_prefix}{package_name}', package_name)
            os.rename(disabled_package_dir, enabled_package_file)
        
        print(f'Enabled package "{package_name}" by renaming it back.')
    
    except FileNotFoundError:
        print(f'Package "{package_name}" was not disabled.')

def remove_pth_file(package_name, site_packages_dir):
    pth_file_path = os.path.join(site_packages_dir, f'{package_name}.pth')
    try:
        if os.path.isfile(pth_file_path):
            os.remove(pth_file_path)
            print(f'Removed .pth file for package "{package_name}".')
        else:
            print(f'No .pth file found for package "{package_name}".')

    except FileNotFoundError:
        print(f'.pth file for package "{package_name}" not found.')

def replace_env_vars(path):
    """
    Replaces environment variables in the path with their actual values.
    Supports both $VAR and ${VAR} formats.
    """
    pattern = re.compile(r'\$(\w+)|\${(\w+)}|\$\((\w+)\)')

    def replace_match(match):
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, '')

    return pattern.sub(replace_match, path)


def restore_packages_with_pth(venv_dir, local_path_file):
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
            
            # Enable the package (revert the disabled state)
            enable_package(package_name, site_packages_dir)

            # Remove the corresponding .pth file
            remove_pth_file(package_name, site_packages_dir)

    print('Successfully restored packages and removed .pth files.')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python restore_packages_with_pth.py '
              '<venv_dir> <local_path_file>')
        sys.exit(1)

    venv_dir = sys.argv[1]
    local_path_file = sys.argv[2]
    restore_packages_with_pth(venv_dir, local_path_file)
