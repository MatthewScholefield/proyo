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
