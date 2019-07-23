import sys

import re
import traceback
from enum import Enum
from os import listdir, chdir, makedirs
from os.path import join, basename, isdir, isfile
from traceback import print_exc, format_exc


class Phase(Enum):
    PARSE = 1
    RUN = 2
    POST_RUN = 2


class ConfigContext:
    def __init__(self, proyo, params):
        self.proyo = proyo
        self.params = params
        self.config = None

    def __enter__(self):
        self.config = dict(self.proyo.config_val)
        self.proyo.config_val.update(self.config, **self.params)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.proyo.config_val.clear()
        self.proyo.config_val.update(self.config)


class Proyo:
    def __init__(self, folder, variables, macros):
        self.root = folder
        self.target = None
        self._variables = variables
        self.macros = macros
        self.update()
        self.config_val = dict(collect_files=True, var_regex=r'{{(.*?)}}')
        self.files = {}
        self.ran_files = {}
        self.generated_files = set()
        self.subs = {}

    def set_target(self, target):
        self.target = target
        for folder, proyo in self.subs.items():
            proyo.set_target(join(target, folder))

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
            sub.config_val = dict(self.config_val)
            sub.files = self.files
            sub.ran_files = self.ran_files
            self.subs[subfolder] = sub
        self.subs[subfolder].update(**new_vars)
        return self.subs[subfolder]

    def config(self, **params):
        missing_keys = set(params) - set(self.config_val)
        for key in missing_keys:
            print('Warning, unknown config key: "{}"'.format(key))
        self.config_val.update(params)

    def config_context(self, **params):
        return ConfigContext(self, params)

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
        makedirs(self.target, exist_ok=True)
        chdir(self.target)
        parent = join(self.root, subpath) if subpath else self.root
        files_to_generate = set()
        for i in sorted(listdir(parent)):
            filename = join(parent, i)
            if isdir(filename):
                self.run(join(subpath, i))
            else:
                if i.startswith('_') and i.endswith('_'):
                    if not subpath:  # Only run files in root dir
                        self.ran_files[filename] = self
                        self._run_text(self._load_text(filename), filename)
                else:
                    if filename in self.generated_files:
                        continue
                    files_to_generate.add(filename)
        if self.config_val['collect_files']:
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

    def post_run_all(self):
        for filename, proyo in self.ran_files.items():
            makedirs(proyo.target, exist_ok=True)
            chdir(proyo.target)
            Proyo._post_run_text(proyo, Proyo._load_text(proyo, filename), filename)

    def _load_text(self, filename):
        base = basename(filename)
        if base in self.macros:
            return self.macros[base]
        with open(filename) as f:
            return f.read()

    def _extract_part(self, text, part_id):
        parts = re.split(r'^\s*#\s*~{3,}.*', text, flags=re.MULTILINE)
        if len(parts) > part_id:
            return parts[part_id]
        return None

    def _parse_text(self, text, label):
        part = self._extract_part(text, 0)
        if part is None:
            return
        self._run_chunk('parsing', part, label, Phase.PARSE)

    def _run_text(self, text, label):
        part = self._extract_part(text, 1)
        if part is None:
            return
        self._run_chunk('running', part, label, Phase.RUN)

    def _post_run_text(self, text, label):
        part = self._extract_part(text, 2)
        if part is None:
            return
        self._run_chunk('post-running', part, label, Phase.POST_RUN)

    def _convert_bash_cmd(self, match):
        command = match.group(1).replace("'", r"\'")
        command = re.sub(r'(?<!\\){(.*?)(?<!\\)}', r"''' + str(\1) + '''", command)
        return "__import__('subprocess').check_call('''" + command + "''', shell=True)"

    def _run_chunk(self, action, chunk, label, phase):
        import_matches = list(re.finditer(r'^\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*\.\.\.\s*', chunk, re.MULTILINE))
        export_matches = list(re.finditer(r'^\s*\.\.\.\s*=\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*', chunk, re.MULTILINE))
        imports = {i.group(1) for i in import_matches}
        exports = {i.group(1) for i in export_matches}

        not_found = imports - set(self._variables)
        if not_found:
            print('Warning when {} {}: Could not resolve variables: {}'.format(action, label, ', '.join(not_found)))
            return

        spans = [(0, 0)] + [i.span() for i in import_matches + export_matches] + [(len(chunk), len(chunk))]
        chunk = ''.join(chunk[b:c] for (a, b), (c, d) in zip(spans, spans[1:]))
        chunk = re.sub('^#?\s*!(.*)', self._convert_bash_cmd, chunk, flags=re.MULTILINE)

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
                eval_code = (
                    "_lines.append(_re.sub("
                    "   _config_val['var_regex'],"
                    "   lambda m, _vars=locals(): eval(m.group(1), {{}}, _vars),"
                    "   '''{}'''"
                    "))"
                )
                exec_lines.append(indent + eval_code.format(
                    '\n'.join(in_between).replace(r"'", r"\'").replace("'''", "''' + \"'''\" + '''")
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
            self._variables['_config_val'] = self.config_val
            self._variables['_re'] = re
            exec('\n'.join(exec_lines), {}, self._variables)
        except Exception as e:
            print_exc()
            print('Error when generating {}, {}: {}'.format(relative, e.__class__.__name__, str(e)))
            return
        vars = re.findall(self.config_val['var_regex'], relative)
        if all(self._variables.get(var) for var in vars) and lines:
            relative = re.sub(self.config_val['var_regex'], lambda m: eval(m.group(1), self._variables), relative)
            self.files[relative] = '\n'.join(lines)
