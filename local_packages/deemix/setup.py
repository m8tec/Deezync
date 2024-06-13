#!/usr/bin/env python3
import pathlib
from setuptools import find_packages, setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name="deemix",
    version="3.6.6",
    description="A barebone deezer downloader library",
    long_description=README,
    long_description_content_type="text/markdown",
    author="RemixDev",
    author_email="RemixDev64@gmail.com",
    license="GPL3",
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    install_requires=["click", "pycryptodomex", "mutagen", "requests", "deezer-py>=1.3.0"],
    extras_require={
        "spotify": ["spotipy>=2.11.0"]
    },
    entry_points={
        "console_scripts": [
            "deemix=deemix.__main__:download",
        ]
    },
)
