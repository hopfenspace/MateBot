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
    license="GLPv3",
    install_requires=[
        "aiohttp>=3.8,<4.0",
        "alembic>=1.7.6,<2.0",
        "fastapi==0.74.1",
        "pydantic>=1.8.2,<2.0",
        "python-jose>=3.3.0,<4.0",
        "python-multipart==0.0.5",
        "requests>=2.26.0,<3.0",
        "SQLAlchemy>=1.4.30,<2.0",
        "uvicorn>=0.17.0,<1.0"
    ],
    extra_requires={
        "full": [
            "aiofiles>=0.8.0,<1.0",
            "ujson>=4.0,<5.0"
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
