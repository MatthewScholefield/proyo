# +++

## Development

{{title_name}} uses Rye for dependency management and development workflow. To get started with development, ensure you have [Rye](https://github.com/astral-sh/rye) installed and then clone the repository and set up the environment:

```sh
git clone https://github.com/MatthewScholefield/patchpy.git
cd patchpy
rye sync
rye run pre-commit install

# Run tests
rye test
```
