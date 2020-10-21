import os
from setuptools import setup, find_packages

from ncpi_fhir_utility.config import FHIR_VERSION

root_dir = os.path.dirname(os.path.abspath(__file__))
req_file = os.path.join(root_dir, "requirements.txt")
with open(req_file) as f:
    requirements = f.read().splitlines()

setup(
    name="fhir-walk",
    description=f"AnVIL FHIR Walker {FHIR_VERSION}",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    scripts=[],
)
