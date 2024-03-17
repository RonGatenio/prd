from setuptools import setup, find_packages

NAME = 'pycprd'

with open("README.md", "r") as fh:
    long_description = fh.read()

# Read requirements from requirements.txt
with open("requirements.txt", "r") as req_file:
    requirements = req_file.read().splitlines()

setup(
    name=NAME,
    version="1.0",
    author="Ron Gatenio",
    author_email="ron.gatenio@gmail.com",
    description="A Concurrent Persistency Race Bug Detector",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            f"{NAME} = pycprd.run:main",
        ],
    },
)
