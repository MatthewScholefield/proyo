from setuptools import setup

setup(
    name='proyo',
    version='0.1.2',
    description='A tool to broadcast notifications across various interfaces',
    url='https://github.com/matthewscholefield/proyo',
    author='Matthew Scholefield',
    author_email='matthew331199@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='notify server',
    packages=['proyo'],
    install_requires=[
    ],
    entry_points={
        'console_scripts': [
            'proyo=proyo.__main__:main',
        ],
    }
)
