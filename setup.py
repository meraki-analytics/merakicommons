from os import path

from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.rst"), encoding="UTF-8") as readme:
    long_description = readme.read()

setup(
    name="merakicommons",
    version="0.0.1.dev3",
    author="Meraki Analytics Team",
    author_email="team@merakianalytics.com",
    url="https://github.com/meraki-analytics/merakicommons",
    description="Common toolset for Meraki Analaytics projects",
    long_description=long_description,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries"
    ],
    license="MIT",
    packages=find_packages(),
    zip_safe=True,
    install_requires=[
    ],
    extras_require={
        "testing": ["pytest", "flake8"]
    }
)
