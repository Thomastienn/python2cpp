from setuptools import setup, find_packages

def get_requirement():
    with open('requirements.txt') as f:
        return f.read().splitlines()

setup(
    name = "py2cpp",
    version = "1.0",
    description = "Python to C++ converter",
    author = "Thomastien",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages = find_packages(),
    include_package_data = True,
    install_requires = get_requirement(),
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'py2c=py2c.commands.cli:main',
        ],
    },
)

