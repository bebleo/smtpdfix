from setuptools import setup

setup(
    name="smtpdfix",
    install_requires=[
        "aiosmtpd >= 1.3.1, <= 1.4.2",
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
)
