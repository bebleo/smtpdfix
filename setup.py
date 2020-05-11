from setuptools import setup, find_packages

version = "0.1.0"

with open("README.md", "rt", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="bebleo-smtpd-fixture",
    version=version,
    author="James Warne",
    author_email="bebleo@yahoo.com",
    description="A tiny SMTP server for use as a test fixture.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    url="https://github.com/bebleo/bebleo-smtpd-fixture",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "pytest"
    ],
)
