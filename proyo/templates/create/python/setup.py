# ~ with proyo.config_as(var_regex=r'# ---(.*?)--- #'):
# ---gen_license_header('#')--- #
# ~ #
from setuptools import setup

setup(
    name='{{project_name}}',
    version='0.1.0',
    description='{{tagline or "<description>"}}',
    url='https://github.com/GIT_USER/{{project_name}}',
    author='{{git_author or "AUTHOR"}}',
    author_email='{{git_email or "AUTHOR_EMAIL"}}',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='{{project_name.replace("-", " ")}}',
    # ~ if is_package:
    packages=['{{module_name}}'],
    # ~ #
    # ~ else:
    py_modules=['{{module_name}}'],
    # ~ #
    install_requires=[],
    # ~ if project_type == 'script':
    entry_points={
        'console_scripts': [
            # ~ if is_package:
            '{{script_name}}={{package_name}}.__main__:main'
            # ~ #
            # ~ else:
            '{{script_name}}={{module_name}}:main'
            # ~ #
        ],
    }
    # ~ #
)
