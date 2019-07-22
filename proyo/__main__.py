import json
from argparse import ArgumentParser
from os import listdir, makedirs
from os.path import join, dirname, isfile, exists, realpath

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
    templates = join(root_dir, 'template')
    macros = load_macros(join(root_dir, 'macros'))

    parser = ArgumentParser()

    proyo = Proyo(templates, dict(parser=parser), macros)
    proyo.parse()

    parser_tree = map_tree(lambda p: p.get_var('parser'), arrange_tree(proyo.get_all_children()))
    for p in collect_leaves(dict(parser_tree)):
        p.add_argument('project_folder')

    for p in proyo.get_all_children():
        if 'parser' in p:
            p['parser'].usage = generate_alternate_help(p)

    args = parser.parse_args()

    out_folder = realpath(args.project_folder)
    if exists(out_folder):
        print('Destination must not exists!')
        exit(1)

    proyo.update_global(vars(args), args=args)
    proyo.run()

    for rel, text in proyo.files.items():
        path = join(out_folder, rel)
        makedirs(dirname(path), exist_ok=True)
        fmt = 'wb' if isinstance(text, bytes) else 'w'
        with open(path, fmt) as f:
            f.write(text)
    print('Generated to {}: {}'.format(args.project_folder, json.dumps(list(proyo.files), indent=2)))


if __name__ == '__main__':
    main()
