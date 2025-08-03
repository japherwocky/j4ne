from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="j4ne",
    version="0.1.0",
    description="A chat bot with data visualizations for IRC, Discord, and Twitter",
    author="japherwocky",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "j4ne=j4ne:main",
        ],
    },
    python_requires=">=3.7",
)
