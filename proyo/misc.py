import re
from copy import deepcopy

from os.path import dirname, abspath, split
from pkg_resources import resource_filename, Requirement

root_dir = resource_filename(Requirement.parse("proyo"), 'proyo')


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


def extract_parts(usage):
    """Extract individual components from a usage string"""
    opp = {'{': '}', '[': ']', '(': ')'}
    cur_word = []
    tokens = []
    stack = []
    for c in usage:
        if c.isspace() and not stack:
            if cur_word:
                tokens.append(''.join(cur_word))
                cur_word.clear()
        elif c in '{[(':
            stack.append(c)
            cur_word.append(c)
        elif c in '}])' and stack and c == opp[stack[-1]]:
            stack.pop()
            cur_word.append(c)
            if not stack and cur_word:
                tokens.append(''.join(cur_word))
                cur_word.clear()
        else:
            cur_word.append(c)
    if cur_word:
        tokens.append(''.join(cur_word))
    return tokens


def remove_redundancy(tree, val_label='_', parent_set=None):
    my_vals = tree.pop(val_label, []) or []
    yield val_label, [i for i in my_vals if i not in (parent_set or set())]
    for key, child in tree.items():
        yield key, dict(remove_redundancy(child, val_label, parent_set=set(my_vals)))


def extract_brace_parts(usage_part):
    m = re.match(r'{(([^,}]+,)*[^}]+)}', usage_part)
    if not m:
        return []
    return m.group(1).split(',')


def remove_redundant_usage(usage_parts_tree, val_label='_'):
    parts = set(usage_parts_tree.pop(val_label, []))
    yield val_label, [i for i in parts if
                      not extract_brace_parts(i) or set(extract_brace_parts(i)) != set(usage_parts_tree)]
    for key, val in usage_parts_tree.items():
        yield key, dict(remove_redundant_usage(val, val_label))


def generate_alternate_help(proyo):
    val_label = '_'
    usage_parts = dict(map_tree(
        lambda x: extract_parts(re.sub(r'\s{2,}', ' ', x['parser'].format_usage().split('[-h]')[-1].strip())),
        arrange_tree(proyo.get_all_children(), val_label)
    ))
    usage_parts = dict(remove_redundant_usage(usage_parts))
    leaves = [set(i) for i in collect_leaves(deepcopy(usage_parts), val_label)] or [set()]
    common = leaves[0].intersection(*leaves[1:])
    usages = dict(map_tree(lambda x: ' '.join([i for i in x if i not in common]), usage_parts))
    tree_usage = '\n'.join(format_tree(usages, val_label, indent='  '))
    original_parts = extract_parts(proyo['parser'].format_usage().replace('usage: ', ''))
    return (
            ' '.join(original_parts) +
            (' '.join([''] + list(common))) * (original_parts and original_parts[-1] == '...') +
            ('\n  │\n' + tree_usage) * bool(tree_usage)
    )
