# Welcome to My Awesome Notebooks

This is an example of deploying notebooks directly from EMR Studio to a public website.

## Overview

This makes use of the [mknotebooks](https://github.com/greenape/mknotebooks) extension.

By combining that and a CodePipeline, any changes to the git repository get deployed to an S3 bucket.

## Project layout

    mkdocs.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.
    docs/notebooks/
        *.ipynb   # Jupyter notebooks that get automatically converted

## Rendering

Notebooks placed in `docs/` are automatically made available without the `.ipynb` extension:

    docs/notebook.ipynb --> https://siteurl/notebook/

You can also add notebooks to your nav in `mkdocs.yml`:

```yaml
# Enable the mknotebooks plugin
plugins:
  - mknotebooks

nav:
  - Home: index.md
  - Notebooks:
    - Oura Sleep Analysis: notebooks.damons_sleep.ipynb

```

