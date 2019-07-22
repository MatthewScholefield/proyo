import sys

import re
import traceback
from enum import Enum
from os import listdir
from os.path import join, basename, isdir, isfile
from traceback import print_exc, format_exc


class Phase(Enum):
    PARSE = 1
    RUN = 2


class Proyo:
    def __init__(self, folder, variables, macros):
        self.root = folder
        self._variables = variables
        self.macros = macros
        self.update()
        self._config = dict(collect_files=True)
        self.files = {}
        self.generated_files = set()
        self.subs = {}

    def __contains__(self, item):
        return item in self._variables

    def __getitem__(self, item):
        return self._variables[item]

    def get_var(self, var, default=None):
        return self._variables.get(var, default)

    def sub(self, subfolder, **new_vars):
        if subfolder not in self.subs:
            folder = join(self.root, subfolder)
            if not isdir(folder):
                raise ValueError('Subdirectory does not exist: ' + folder)
            sub = Proyo(folder, dict(self._variables, **new_vars), self.macros)
            sub.generated_files = self.generated_files
            sub._config = dict(self._config)
            sub.files = self.files
            self.subs[subfolder] = sub
        self.subs[subfolder].update(**new_vars)
        return self.subs[subfolder]

    def config(self, **params):
        self._config.update(params)

    def get_all_children(self):
        return [self] + sum([i.get_all_children() for i in self.subs.values()], [])

    def update(self, val=None, **params):
        self._variables.update(val or {}, **params, folder=self.root, proyo=self)

    def update_global(self, val=None, **params):
        self.update(val, **params)
        for sub in self.subs.values():
            sub.update_global(val, **params)

    def parse(self):
        for i in sorted(listdir(self.root)):
            filename = join(self.root, i)
            if isfile(filename) and i.startswith('_') and i.endswith('_'):
                try:
                    self._parse_text(self._load_text(filename), filename)
                except Exception:
                    print('Failed to parse {}: {}'.format(filename, ''.join(
                        '\n    | ' + i for i in format_exc().strip().split('\n'))))
                    print()

    def run(self, subpath=''):
        parent = join(self.root, subpath) if subpath else self.root
        files_to_generate = set()
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
                    files_to_generate.add(filename)
        if self._config['collect_files']:
            for filename in files_to_generate:
                relative = join(subpath, basename(filename))
                try:
                    with open(filename) as f:
                        self._gen_file(f.read(), relative, filename)
                except UnicodeDecodeError:
                    with open(filename, 'rb') as f:
                        data = f.read()
                    self.files[relative] = data
                except Exception:
                    print('Failed to generate {}: {}'.format(filename, ''.join(
                        '\n    ' + i for i in format_exc().split('\n'))))

    def _load_text(self, filename):
        base = basename(filename)
        if base in self.macros:
            return self.macros[base]
        with open(filename) as f:
            return f.read()

    def _parse_text(self, text, label):
        before, *after = re.split(r'^\s*#\s*~{3,}.*', text, flags=re.MULTILINE)
        self._run_chunk('parsing', before, label, Phase.PARSE)

    def _run_text(self, text, label):
        *before, after = re.split(r'^\s*#\s*~{3,}.*', text, flags=re.MULTILINE)
        if not before:
            return
        self._run_chunk('running', after, label, Phase.RUN)

    def _run_chunk(self, action, chunk, label, phase):
        import_matches = list(re.finditer(r'^\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*\.\.\.\s*', chunk, re.MULTILINE))
        export_matches = list(re.finditer(r'^\s*\.\.\.\s*=\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*', chunk, re.MULTILINE))
        imports = {i.group(1) for i in import_matches}
        exports = {i.group(1) for i in export_matches}

        spans = [(0, 0)] + [i.span() for i in import_matches + export_matches] + [(len(chunk), len(chunk))]
        chunk = ''.join(chunk[b:c] for (a, b), (c, d) in zip(spans, spans[1:]))

        not_found = imports - set(self._variables)
        if not_found:
            print('Warning when {} {}: Could not resolve variables: {}'.format(action, label, ', '.join(not_found)))
            return

        variables = {i: self._variables[i] for i in imports}
        try:
            exec(chunk, {}, variables)
            extra_exports = exports - set(variables)
            if extra_exports:
                raise NameError("Could not resolve variables: {}".format(extra_exports))
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
            export_vars = {i: variables[i] for i in exports}
            if phase == Phase.RUN:
                self.update_global(export_vars)
            elif phase == Phase.PARSE:
                self.update(export_vars)
            return
        lines = chunk.split('\n')
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
            self._variables['_lines'] = lines = []
            exec('\n'.join(exec_lines), {}, self._variables)
        except Exception as e:
            print_exc()
            print('Error when generating {}, {}: {}'.format(relative, e.__class__.__name__, str(e)))
            return
        vars = re.findall(r'{{(.*?)}}', relative)
        if all(self._variables.get(var) for var in vars) and lines:
            relative = re.sub(r'{{(.*?)}}', lambda m: eval(m.group(1), self._variables), relative)
            self.files[relative] = '\n'.join(lines)
