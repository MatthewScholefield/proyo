import sys

import re
import traceback
from os import listdir
from os.path import join, basename, isdir, isfile, splitext
from traceback import print_exc, format_exc


class Proyo:
    def __init__(self, folder, variables, macros):
        self.root = folder
        self.variables = variables
        self.macros = macros
        self.update()
        self.files = {}
        self.generated_files = set()
        self.subs = {}

    def sub(self, subfolder, **new_vars):
        if subfolder not in self.subs:
            folder = join(self.root, subfolder)
            if not isdir(folder):
                raise ValueError('Subdirectory does not exist: ' + folder)
            sub = Proyo(folder, dict(self.variables, **new_vars), self.macros)
            sub.generated_files = self.generated_files
            sub.files = self.files
            self.subs[subfolder] = sub
        self.subs[subfolder].update(self.variables, **new_vars)
        return self.subs[subfolder]

    def update(self, val=None, **params):
        self.variables.update(val or {}, **params, folder=self.root, proyo=self)

    def parse(self):
        for i in sorted(listdir(self.root)):
            filename = join(self.root, i)
            if isfile(filename) and i.startswith('_') and i.endswith('_'):
                try:
                    self._parse_text(self._load_text(filename), filename)
                except Exception:
                    print('Failed to parse {}: {}'.format(filename, ''.join('\n    | ' + i for i in format_exc().strip().split('\n'))))
                    print()

    def run(self, subpath=''):
        parent = join(self.root, subpath) if subpath else self.root
        for i in sorted(listdir(parent)):
            filename = join(parent, i)
            if isdir(filename):
                self.run(join(subpath, i))
            else:
                if i.startswith('_') and i.endswith('_'):
                    self._run_text(self._load_text(filename), filename)
                else:
                    if filename in self.generated_files:
                        continue
                    self.generated_files.add(filename)
                    relative = join(subpath, i)
                    try:
                        with open(filename) as f:
                            try:
                                self._gen_file(f.read(), relative, filename)
                            except Exception:
                                print('Failed to generate {}: {}'.format(filename, ''.join(
                                    '\n    ' + i for i in format_exc().split('\n'))))
                    except UnicodeDecodeError:
                        with open(filename, 'rb') as f:
                            data = f.read()
                        self.files[relative] = data

    def _load_text(self, filename):
        base = basename(filename)
        if base in self.macros:
            return self.macros[base]
        with open(filename) as f:
            return f.read()

    def _parse_text(self, text, label):
        before, *after = re.split(r'^\s*#\s*~{3,}.*', text, flags=re.MULTILINE)
        self._run_chunk('parsing', before, label)

    def _run_text(self, text, label):
        *before, after = re.split(r'^\s*#\s*~{3,}.*', text, flags=re.MULTILINE)
        if not before:
            return
        self._run_chunk('running', after, label)

    def _run_chunk(self, action, chunk, label):
        sections = re.split(r'^\s*...\s*$', chunk, flags=re.MULTILINE)
        if len(sections) > 2:
            raise ValueError('Too many ... sections')
        if len(sections) == 2:
            var_lines, data = sections
        else:
            var_lines, data = '', sections[0]
        var_names = re.findall(r'^\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*\.\.\.\s*', var_lines, re.MULTILINE)
        not_found = set(var_names) - set(self.variables)
        if not_found:
            print('Warning when {} {}: Could not resolve variables: {}'.format(action, label, ', '.join(not_found)))
            return
        try:
            exec(data, {}, self.variables)
        except SyntaxError as e:
            print_exc()
            error_class = e.__class__.__name__
            detail = e.args[0] if e.args else ''
            line_number = e.lineno
        except Exception as e:
            error_class = e.__class__.__name__
            detail = e.args[0] if e.args else ''
            cl, exc, tb = sys.exc_info()
            line_number = traceback.extract_tb(tb)[-1][1]
        else:
            return
        lines = data.split('\n')
        print('Error when {} {}, {}: {}'.format(action, label, error_class, detail))
        if line_number <= len(lines):
            print('Line {}: {}'.format(line_number, lines[line_number - 1]))
        else:
            print('On line', line_number)
        print()
        return

    def _gen_file(self, content, relative, filename):
        exec_lines = []
        in_between = []
        indent = ''

        def flush_between():
            if in_between:
                exec_lines.append(indent + "_lines.append('''{}''')".format(
                    re.sub(r'{{(.*?)}}', r"''' + str(\1) + '''", '\n'.join(in_between).replace(r"'", r"\'")
                           .replace("'''", "''' + \"'''\" + '''"))
                ))
                in_between.clear()

        for line in content.split('\n'):
            if re.match(r'\s*#\s*~(?!~)', line):
                code_line = line.split('~', 1)[-1].strip()
                flush_between()
                if not code_line:
                    if not indent:
                        print_exc()
                        print('Error when generating {}: Too many unindents'.format(relative))
                        return
                    indent = indent[1:]
                else:
                    exec_lines.append(indent + code_line)
                    if code_line.endswith(':'):
                        indent += ' '
            else:
                in_between.append(line)
        flush_between()
        if indent:
            print_exc()
            print('Error when generating {}: {} indents remaining at end of file'.format(relative, len(indent)))
            return
        try:
            self.variables['_lines'] = lines = []
            exec('\n'.join(exec_lines), {}, self.variables)
        except Exception as e:
            print_exc()
            print('Error when generating {}, {}: {}'.format(relative, e.__class__.__name__, str(e)))
            return
        vars = re.findall(r'{{(.*?)}}', relative)
        if all(self.variables.get(var) for var in vars) and lines:
            relative = re.sub(r'{{(.*?)}}', lambda m: eval(m.group(1), self.variables), relative)
            self.files[relative] = '\n'.join(lines)
