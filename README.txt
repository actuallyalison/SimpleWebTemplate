This is a tool to build menus and other repeated content by stitching together HTML from separate files.
It also compiles markdown (.md) files into HTML.

Use:

TL;DR version:

install pyyaml and markdown
run main.py and pass it the local name of a subfolder
subfolder is expected to contain folders named "source" and "dictionary",
    which contain html/markdown/templating and yaml files respectively.
outputs to build folder (creates if necessary)
templates are of the form: {{ file:: [filename w relative path] }} and {{ value:: [key to a yaml dictionary] }}
templates can be nested to arbitrary depth but no circular dependencies
markdown files cannot contain template tags but can be used as template tag targets


Full explanation:

Requires python 3 with markdown and yaml.
After installing python 3 (from python.org), at a command prompt run:
pip3 install pyyaml
pip3 install markdown

To compile the sample site, run from command prompt:
python3 main.py sample_blog

This compiles markdown files in source to html files in target, replaces value tags in files with the values from
the dictionary folder, and replaces file tags with the contents of the actual files.

Values tags are ex.:
{{ value:: site-root }}
which pulls the site-root value from dictionary/template_values.yml in order to let you use fully qualified URLs and
still test the site on localhost by switching which value you use.

Files tags are ex.:
{{ file:: /menus/header.html }}
which pulls the main menu into each html page.
Note that the header and footer together form a complete HTML page skeleton but on their own they are broken code.

There are many ways to use this, but the sample site has a working setup that follows a couple key rules:

Markdown files can't contain {{ }} tags. This is because markdown compilation has to happen before tags are resolved
so that html files can embed markdown.

To embed markdown files, the {{ file:: }} tag needs to reference [name of markdown file].html, which doesn't exist in
source and is created from the markdown. For example, if you have index.html embed index_contents.md, you would use
{{ file:: index_contents.html }}

This also means you can't name a markdown file and an html file the same base name because the markdown file will
compile to that other name. So a good convention is a page that embeds its own name as markdown adds _contents to the
name for the markdown file as in the previous paragraph.




