from setuptools import find_packages, setup

setup(
    name="min_kamp",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "streamlit==1.41.1",
        "pandas==2.2.3",
        "numpy==2.0.2",
        "sqlalchemy",  # Legg til database-avhengigheter
        "python-dotenv",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-mock",
            "flake8",
            "black",
        ],
    },
    author="Tor Inge Jossang",
    description="Fotballlag management application",
    long_description=open("README.md").read() if open("README.md").read() else "",
    long_description_content_type="text/markdown",
    url="https://github.com/toro68/min_kamp",
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
