from setuptools import setup, find_packages

setup(
    name="min_kamp",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "streamlit>=1.24.0",
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "python-dotenv>=1.0.0",
        "SQLAlchemy>=2.0.0",
        "bcrypt>=4.0.0",
        "python-jose>=3.3.0",
        "passlib>=1.7.4",
    ],
    python_requires=">=3.9",
)
