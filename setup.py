from setuptools import setup, find_packages

version = "0.2.3"

with open("README.md", "rt", encoding="utf-8") as f:
    long_description = f.read()

short_description = ("A mock SMTP server designed for use as a test fixture "
                     "that implements encryption and authentication to mimic "
                     "a real world server.")

setup(
    name="bebleo-smtpd-fixture",
    version=version,
    author="James Warne",
    author_email="bebleo@yahoo.com",
    description=short_description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={
        "bebleo_smtpd_fixture": ["certs/*.pem"]
    },
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
        "aiosmtpd",
        "python-dotenv <= 0.14.0",
        "pytest"
    ],
)
