import os
import re
import setuptools
from typing import List


def get_content(file: str) -> str:
    with open(file, "r", encoding="utf-8") as f:
        return f.read()


def get_version(package: str) -> str:
    path = os.path.join(package, "__init__.py")
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", get_content(path)).group(1)


def get_packages(package: str) -> List[str]:
    return [
        directory
        for directory, subdirectories, filenames in os.walk(package)
        if os.path.exists(os.path.join(directory, "__init__.py"))
    ]


setuptools.setup(
    name="matebot_core",
    version=get_version("matebot_core"),
    packages=get_packages("matebot_core"),
    author="Chris",
    author_email="chris@hopfen.space",
    description="MateBot core API",
    long_description=get_content("README.md"),
    long_description_content_type="text/markdown",
    install_requires=[
        "fastapi>=0.66",
        "pydantic>=1.8",
        "requests>=2.20",
        "SQLAlchemy>=1.4",
        "uvicorn>=0.14"
    ],
    extra_requires={
        "full": [
            "aiofiles>=0.7",
            "ujson>=4.0"
        ]
    },
    project_urls={},
    python_requires=">=3.7",
    classifiers=[
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Development Status :: 3 - Alpha"
    ]
)
