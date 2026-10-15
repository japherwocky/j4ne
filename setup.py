from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="j4ne",
    version="0.1.0",
    description="A chat bot with CLI and web interfaces for IRC and Slack",
    author="japherwocky",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            # The Typer app; j4ne:main is its callback and needs a context
            "j4ne=j4ne:app",
        ],
    },
    python_requires=">=3.10",
)

