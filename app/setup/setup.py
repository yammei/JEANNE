import os
from setuptools import setup

requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')

with open(requirements_path) as f:
    requirements = f.read().splitlines()

setup(
    name="Locator",
    version="1.0",
    install_requires=requirements,
)
