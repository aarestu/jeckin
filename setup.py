import pathlib

from setuptools import setup, find_packages

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name='jeckin',
    version='0.0.1b7',
    python_requires=">=3.7, <4",

    author="Restu Suhendar",
    author_email="restu.suhendar@gmail.com",
    project_urls={
        "Source": "https://github.com/aarestu/jeckin",
        "Issues": "https://github.com/aarestu/jeckin/issues",
    },
    description="SSH HTTP Injector",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(include=['jeckin', 'jeckin.*']),
    include_package_data=True,
    install_requires=[
        "paramiko>=2.4"
    ],

    entry_points={
        'console_scripts': ['jeckin=jeckin.main:main']
    },

    keywords=['python', 'ssh', 'injector', 'free internet', 'tunneling', 'internet gratis', 'http injector'],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ]
)
