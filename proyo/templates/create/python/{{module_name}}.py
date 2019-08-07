# ~ if project_type == 'script':
# ~ with proyo.config_as(var_regex=r'# ---(.*?)--- #'):
# ---gen_license_header('#')--- #
# ~ #
from argparse import ArgumentParser


def main():
    parser = ArgumentParser(description='{{description or tagline or ""}}')
    args = parser.parse_args()


if __name__ == '__main__':
    main()
# ~ #
# ~ else:
# ~ class_name = ''.join(w[0].upper() + w[1:] for w in module_name.split('_'))
# ~ with proyo.config_as(var_regex=r'___(.*?)___'):
class ___class_name___:
    """{{tagline}}"""
    def __init__(self):
        pass
# ~ #
# ~ #
