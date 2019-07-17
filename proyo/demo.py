_lines = []
project_name = ''
module_name = ''
as_package = False
project_type = 'script'
script_name = 'something'
package_name = ''

_lines.append('''from setuptools import setup

setup(
    name=\'''' + str(project_name) + '''\',
    version=\'0.1.0\',
    description=\'Script description\',
    url=\'https://github.com/someuser/somerepo\',
    author=\'First Last\',
    author_email=\'email.user@provider.com\',
    classifiers=[
        \'Development Status :: 3 - Alpha\',

        \'Intended Audience :: Developers\',
        \'Programming Language :: Python :: 3\',
        \'Programming Language :: Python :: 3.4\',
        \'Programming Language :: Python :: 3.5\',
        \'Programming Language :: Python :: 3.6\',
    ],
    keywords=\'project keywords here\',''')
if as_package:
 _lines.append('''    py_modules=[\'''' + str(module_name) + '''\'],''')
else:
 _lines.append('''    packages=[\'''' + str(module_name) + '''\'],''')
_lines.append('''    install_requires=[],''')
if project_type == 'script':
 _lines.append('''    entry_points={
        \'console_scripts\': [''')
 if as_package:
  _lines.append('''            \'''' + str(script_name) + '''=''' + str(package_name) + '''.__main__:main\'''')
 else:
  _lines.append('''            \'''' + str(script_name) + '''=''' + str(module_name) + ''':main\'''')
 _lines.append('''        ],
    }''')