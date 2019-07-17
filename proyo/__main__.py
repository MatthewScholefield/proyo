import json
from argparse import ArgumentParser
from os import listdir, makedirs
from os.path import join, dirname, abspath, isfile, exists, realpath, split

from proyo.proyo import Proyo

root = dirname(dirname(abspath(__file__)))


def load_macros(folder):
    macros = {}
    for i in listdir(folder):
        path = join(folder, i)
        if isfile(path):
            with open(path) as f:
                macros[i] = f.read()
    return macros


def main():
    templates = join(root, 'template')
    macros = load_macros(join(root, 'macros'))

    parser = ArgumentParser()
    parser.add_argument('project_folder', help='Destination folder')

    proyo = Proyo(templates, dict(parser=parser), macros)
    proyo.parse()

    args = parser.parse_args()

    out_folder = realpath(args.project_folder)
    if exists(out_folder):
        print('Destination must not exists!')
        exit(1)

    proyo.variables.update(vars(args), args=args)
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
