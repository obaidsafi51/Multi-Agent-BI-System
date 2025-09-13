"""
Setup configuration for the shared models package
"""

from setuptools import setup, find_packages

setup(
    name="shared-models",
    version="1.0.0",
    description="Standardized data models for the Multi-Agent BI System",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
    ],
    author="Multi-Agent BI System",
    author_email="dev@multi-agent-bi.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
