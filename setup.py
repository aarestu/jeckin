from setuptools import setup, find_packages

setup(
    name='jeckin',
    version='0.1.0',
    python_requires=">=3.7, <4",
    packages=find_packages(include=['app', 'jeckin.*']),
    install_requires=[
    ],

    entry_points={
        'console_scripts': ['jeckin=jeckin.main:main']
    }
)