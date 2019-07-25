# Proyo

*A command line tool to create new software projects*

Proyo is a tool to generate boilerplate code for new software projects for any
language. Think [create-react-app](https://facebook.github.io/create-react-app/),
but for any language and framework.

## Usage

Create a new Python script:

```bash
proyo create python script --as-package
```

Create a new React app:

```bash
proyo create react app --license apache
```

Create a new C++ app:

```bash
proyo create cpp app --build-system meson
```

View what templates are available:

```bash
proyo -h
```

## Installation

Install via pip:

```bash
pip3 install proyo
```

## Philosophy

Proyo follows the idea that a good default is better than not choosing at all.
For example, by default apps are created using the MIT license.

## Adding Templates

You can add a new language by creating a new folder in `proyo/templates/create`. Read
more about the powers of Proyo's templating system
[in the tutorial](https://github.com/MatthewScholefield/proyo/wiki/Template-Tutorial).
