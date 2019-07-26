import json
import shutil
from argparse import ArgumentParser
from os import listdir, makedirs, getcwd, chdir
from os.path import join, dirname, isfile, exists, realpath
from subprocess import call, check_output, CalledProcessError

from proyo.misc import root_dir, generate_alternate_help, arrange_tree, map_tree, collect_leaves
from proyo.proyo import Proyo


def load_macros(folder):
    macros = {}
    for i in listdir(folder):
        path = join(folder, i)
        if isfile(path):
            with open(path) as f:
                macros[i] = f.read()
    return macros


def main():
    templates = join(root_dir, 'templates')
    macros = load_macros(join(root_dir, 'macros'))
    cur_dir = getcwd()

    parser = ArgumentParser()

    proyo = Proyo(templates, dict(parser=parser), macros)
    proyo.parse()

    for p in proyo.get_leaf_vars('parser'):
        p.add_argument('project_folder')

    for p in proyo.get_all_children():
        if 'parser' in p:
            p['parser'].usage = generate_alternate_help(p)

    args = parser.parse_args()

    chdir(cur_dir)
    out_folder = realpath(args.project_folder)
    if exists(out_folder):
        print('Destination must not exists!')
        exit(1)

    proyo.set_target(out_folder)
    proyo.update_global(args=args)
    proyo.run()

    chdir(cur_dir)
    for rel, text in proyo.files.items():
        path = join(out_folder, rel)
        makedirs(dirname(path), exist_ok=True)
        fmt = 'wb' if isinstance(text, bytes) else 'w'
        with open(path, fmt) as f:
            f.write(text)

    try:
        tree_output = '\n' + check_output(['tree', '-C', out_folder]).decode().split('\n', 1)[-1]
    except CalledProcessError:
        tree_output = json.dumps(list(proyo.files), indent=2)

    proyo.post_run_all()

    print('Generated to {}: {}'.format(args.project_folder, tree_output))


if __name__ == '__main__':
    main()
