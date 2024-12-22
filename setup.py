from setuptools import setup, find_packages

setup(
    name="min_kamp",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "bcrypt>=4.2.1",
        "pylint>=3.0.3",
    ],
    python_requires=">=3.9",
)
