from setuptools import setup

setup(
    name='something',
    version='0.1.0',
    description='Script description',
    url='https://github.com/someuser/somerepo',
    author='First Last',
    author_email='email.user@provider.com',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='project keywords here',
    packages=['something'],
    install_requires=[],
    entry_points={
        'console_scripts': [
            'something=something:main'
        ],
    }
)
