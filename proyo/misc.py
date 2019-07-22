from os.path import dirname, abspath, split

root_dir = dirname(dirname(abspath(__file__)))


def format_tree(obj, val_label, indent=''):
    obj.pop(val_label, '')
    for num, (key, val) in enumerate(sorted(obj.items())):
        is_end = num == len(obj) - 1
        s = indent + ['├── ', '└── '][is_end] + key
        if isinstance(val, dict) and val_label in val and val[val_label]:
            s += ' ' + val[val_label]
        yield s
        if isinstance(val, dict):
            for i in format_tree(val, val_label, indent + ['│   ', '    '][is_end]):
                yield i


def format_tree_lines(obj, indent=''):
    for num, (key, val) in enumerate(sorted(obj.items())):
        is_end = num == len(obj) - 1
        yield indent + ['├── ', '└── '][is_end] + key
        if isinstance(val, dict):
            for i in format_tree_lines(val, indent + ['│   ', '    '][is_end]):
                yield i


def format_tree_dict(obj, indent=''):
    return '\n'.join(format_tree_lines(obj, indent))


def arrange_tree(proyos, val_label='_'):
    root = {}
    for proyo in proyos:
        if 'parser' not in proyo:
            continue
        path = proyo.root
        parts = []
        while True:
            path, part = split(path)
            if not part:
                break
            parts.append(part)
        if not parts:
            node = root
        else:
            parts = list(reversed(parts))
            node = root
            for part in parts:
                node = node.setdefault(part, {})
        node[val_label] = proyo

    while proyos and val_label not in root and len(root) == 1:
        root = next(iter(root.values()))
    return root


def collect_leaves(tree, val_label='_'):
    parent_val = tree.pop(val_label, None)
    if not tree:
        return [parent_val]
    return sum([collect_leaves(val, val_label) for val in tree.values()], [])


def map_tree(func, tree):
    for key, val in tree.items():
        if isinstance(val, dict):
            yield key, dict(map_tree(func, val))
        else:
            yield key, func(val)


def generate_alternate_help(proyo):
    val_label = '_'
    usages = dict(map_tree(
        lambda x: x['parser'].format_usage().split('[-h]')[-1].strip(),
        arrange_tree(proyo.get_all_children(), val_label)
    ))
    tree_usage = '\n'.join(format_tree(usages, val_label, indent='  '))
    return (
            proyo['parser'].format_usage().replace('usage: ', '') +
            ('  │\n' + tree_usage) * bool(tree_usage)
    )
