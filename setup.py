import pathlib

from setuptools import setup, find_packages

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name='jeckin',
    version='0.0.1b4',
    python_requires=">=3.7, <4",
    description="http injector",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(include=['jeckin', 'jeckin.*']),
    include_package_data=True,
    install_requires=[
    ],

    entry_points={
        'console_scripts': ['jeckin=jeckin.main:main']
    },

    keywords=['python', 'http', 'http injector'],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ]
)
