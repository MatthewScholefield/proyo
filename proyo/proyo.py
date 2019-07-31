import sys

import re
import traceback
from enum import Enum
from os import listdir, chdir, makedirs
from os.path import join, basename, isdir, isfile, dirname
from traceback import print_exc, format_exc

from proyo.misc import map_tree, arrange_tree, collect_leaves


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
        self.config_val = dict(file_exports=None, var_regex=r'{{(.*?)}}', comment='#')
        self.files = {}
        self.ran_files = {}
        self.generated_files = set()
        self.subs = {}
        self.file_exports = None

    def set_target(self, target):
        self.target = target
        for folder, proyo in self.subs.items():
            proyo.set_target(target)

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
        for i in self.subs.values():
            i.config(**params)

    def config_as(self, **params):
        return ConfigContext(self, params)

    def get_all_children(self):
        return [self] + sum([i.get_all_children() for i in self.subs.values()], [])

    def get_leaf_vars(self, var_name):
        sentinel = object()
        parser_tree = map_tree(lambda p: p.get_var(var_name, sentinel), arrange_tree(self.get_all_children()))
        return [i for i in collect_leaves(dict(parser_tree)) if i is not sentinel]

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
                    self._parse_file(filename)
                except Exception:
                    print('Failed to parse {}: {}'.format(filename, ''.join(
                        '\n    | ' + i for i in format_exc().strip().split('\n'))))
                    print()

    def only_collect(self, files):
        self.file_exports = files

    def run(self, subpath=''):
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
                        self._run_file(filename)
                else:
                    if filename in self.generated_files:
                        continue
                    files_to_generate.add(filename)
        file_exports = [join(self.root, i) for i in (files_to_generate if self.file_exports is None else self.file_exports)]
        if self.file_exports is not None and subpath:
            file_exports = []
        for filename in file_exports:
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
            src_sub = dirname(filename)
            if not src_sub.startswith(proyo.root):
                raise RuntimeError('Invalid template source: ' + src_sub)
            target_sub = self.target + src_sub[len(proyo.root):]
            makedirs(target_sub, exist_ok=True)
            chdir(target_sub)

            Proyo._post_run_file(proyo, filename)

    def _load_text(self, filename):
        base = basename(filename)
        if base in self.macros:
            return self.macros[base]
        with open(filename) as f:
            return f.read()

    def _extract_part_text(self, text, part_id):
        parts = re.split(r'^\s*#\s*~{3,}.*', text, flags=re.MULTILINE)
        if len(parts) > part_id:
            return parts[part_id]
        return None

    def _extract_part(self, filename, part_id):
        with open(filename) as f:
            file_text = f.read()
        base = basename(filename)
        if base in self.macros:
            macro_text = self.macros[base]
        else:
            macro_text = ''
        file_part = self._extract_part_text(file_text, part_id)
        macro_part = self._extract_part_text(macro_text, part_id)
        return '\n'.join([macro_part or '', file_part or ''])

    def _parse_file(self, filename, ):
        part = self._extract_part(filename, 0)
        if part is None:
            return
        self._run_chunk('parsing', part, filename, Phase.PARSE)

    def _run_file(self, filename):
        part = self._extract_part(filename, 1)
        if part is None:
            return
        self._run_chunk('running', part, filename, Phase.RUN)

    def _post_run_file(self, filename):
        part = self._extract_part(filename, 2)
        if part is None:
            return
        self._run_chunk('post-running', part, filename, Phase.POST_RUN)

    def _convert_bash_cmd(self, match):
        command = match.group(2)
        exe = command.split(' ')[0]
        command = command.replace("'", r"\'")
        command = re.sub(r'(?<!\\){(.*?)(?<!\\)}', r"''' + str(\1) + '''", command)
        return match.group(1) + "__import__('shutil').which('" + exe + "') and __import__('subprocess').check_call('''" + command + "''', shell=True)"

    def _run_chunk(self, action, chunk, label, phase):
        import_matches = list(re.finditer(r'^\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*\.\.\.\s*', chunk, re.MULTILINE))
        export_matches = list(re.finditer(r'^\s*\.\.\.\s*=\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*', chunk, re.MULTILINE))
        imports = {i.group(1) for i in import_matches}
        exports = {i.group(1) for i in export_matches}

        not_found = imports - set(self._variables)
        if not_found:
            print('Warning when {} {}: Could not resolve variables: {}'.format(action, label, ', '.join(not_found)))
            return

        spans = [(0, 0)] + sorted([i.span() for i in import_matches + export_matches]) + [(len(chunk), len(chunk))]
        chunk = ''.join(chunk[b:c] for (a, b), (c, d) in zip(spans, spans[1:]))
        chunk = re.sub('^(\s*)#\s*!(.*)', self._convert_bash_cmd, chunk, flags=re.MULTILINE)

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
                    "   lambda m, _vars=locals(): str(eval(m.group(1), {{}}, _vars)),"
                    "   '''{}'''"
                    "))"
                )
                exec_lines.append(indent + eval_code.format(
                    '\n'.join(in_between).replace(r"'", r"\'").replace("'''", "''' + \"'''\" + '''")
                ))
                in_between.clear()

        for line in content.split('\n'):
            if re.match(r'\s*' + self.config_val['comment'] + '\s*~', line):
                code_line = line.split('~', 1)[-1].strip()
                flush_between()
                if code_line == '#':
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

        variables = dict(self._variables)
        variables['_lines'] = lines = []
        variables['_config_val'] = self.config_val
        variables['_re'] = re

        try:
            exec('\n'.join(exec_lines), {}, variables)
        except Exception as e:
            print_exc()
            print('Error when generating {}, {}: {}'.format(relative, e.__class__.__name__, str(e)))
            return
        path_vars = re.findall(self.config_val['var_regex'], relative)
        if all(variables.get(var) for var in path_vars) and lines:
            relative = re.sub(self.config_val['var_regex'], lambda m: str(eval(m.group(1), variables)), relative)
            self.files[relative] = '\n'.join(lines).strip() + '\n'
