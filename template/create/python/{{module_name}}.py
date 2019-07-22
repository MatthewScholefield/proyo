# ~ if project_type == 'script':
from argparse import ArgumentParser


def main():
    parser = ArgumentParser()
    args = parser.parse_args()


if __name__ == '__main__':
    main()
# ~
# ~ else:
# ~ class_name = ''.join(w[0].upper() + w[1:] for w in module_name.split('_'))
class {{class_name}}:
    def __init__(self):
        pass
# ~