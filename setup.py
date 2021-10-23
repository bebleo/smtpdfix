from setuptools import setup

setup(
    name="smtpdfix",
    install_requires=[
        "aiosmtpd >= 1.3.1, <= 1.4.2",
        "pytest",
        "python-dotenv",
        "trustme",
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
