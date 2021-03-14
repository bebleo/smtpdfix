from setuptools import find_packages, setup

version = "0.3.0"

with open("README.md", "rt", encoding="utf-8") as f:
    long_description = f.read()

short_description = ("A mock SMTP server designed for use as a test fixture "
                     "that implements encryption and authentication.")

setup(
    name="smtpdfix",
    version=version,
    author="James Warne",
    author_email="bebleo@yahoo.com",
    description=short_description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    url="https://github.com/bebleo/smtpdfix",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Pytest",
    ],
    python_requires=">= 3.6",
    install_requires=[
        "aiosmtpd >= 1.3.1",
        "cryptography >= 3.4.4",
        "pytest",
        "python-dotenv",
    ],
    extras_require={
        "dev": [
            "flake8",
            "isort",
            "pytest-asyncio",
            "pytest-cov",
            "pytest-timeout",
            "tox",
        ],
    },
    entry_points={
        "pytest11": ["smtpd = smtpdfix.fixture"]
    },
)
