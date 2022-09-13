#!/usr/bin/env python3
import re
import yaml
import argparse
import os
import markdown

"""



Functionality:

Crawls through the source folder (default name 'source' or you can drag a folder onto this script or edit build_windows.bat)
and replaces template references with their actual contents in a new copy in the build folder (default 'build'). 

Supports two types of templating currently:

File references:
{{ file:: menus/top_menu.html }}
these will be replaced by the contents of that file.

Value references:
{{ value:: jquery-filename }}
these will be replaced by the value from a key-value pair with that name defined in the YAML file.
Currently this is outside the source folder in the base folder and is called template_values.yaml
Example entry:
jquery-filename: jquery.4.7.js
This would replace the template value entry above (everything between the {{ }} ) with "jquery.4.7.js".

Dependencies:
Requires yaml (pip install pyyaml)

Pseudocode:
    - get argument for target project subfolder 
    - load dictionary keys from any yaml files in dictionary folder
    - delete everything in build folder
    - convert markdown
        - find all .md files in source
        - convert to .html and write to target
    - expand templates
        - load_files
            - load files in source except ~, .swp, and .md
                - '.jpg', '.png', '.gif', 'tiff', '.ico' are loaded as binaries into no_refs
                - other files are assumed text and have their refs catalogued as part of class load
                - ones with refs go into has_refs, ones without into no_refs
            - load files in target except ~, and .swp
                - '.jpg', '.png', '.gif', 'tiff', '.ico' are loaded as binaries into no_refs
                - other files are assumed text and have their refs catalogued as part of class load
                - ones with refs go into has_refs, ones without into no_refs
    - write all loaded files to build folder
         
         
TODO: 
 - make clear out target folder on build be optional

- some way to tag template-only files as something that shouldn't be pushed to output.
    Perhaps introduce one more tag type such as {{ noinclude }} or {{ template }}
    Or can say that any file that is referenced by another file is not itself pushed. Is this too restrictive?
    
- Repeater to avoid having to manually index the files:
    - Create tag: {{ Folder: /foo, Pre: "<div>", Post: "</div>" }} which will generate a link to each item in 
        that folder inside the html wrapper indicated.
    - Create tag: {{ Title: My Blog }} which will be used inside each target item in the folder to affect the 
        display text of the generated links.
    - Nice to haves: option to sort folder by other than file name (the default), and to give finer grained 
        control over how the link itself is generated.

Change history:
11 Sept 2022, AAS - initial check-in to Github after doing a cleanup / refactor.
           

"""


class BinaryFile:
    """Stores binary files for consistency with how TemplateFile works.

    """
    def __init__(self, folder_name, path_name):
        """
        Read in file contents upon init.
        :param folder_name:
        :param path_name:

        """
        self.path_name = path_name
        with open(os.path.join(folder_name, path_name), 'rb') as f:
            self.file_contents = f.read()


class TemplateFile:
    """Stores a file plus metadata about the files or dictionary values referenced.

    Upon load, stores a list of regex matches for {{ }} tags and their targets.
    Crashes if fed binary files so those are filtered out elsewhere by extension currently.
    """
    def __init__(self, folder_name, path_name, template_values):
        """
        Read in file
        :param folder_name:
        :param path_name:
        :param template_values:
        """

        self.path_name = path_name
        self.template_references = {}

        with open(os.path.join(folder_name, path_name), 'r') as f:
            self.file_contents = f.readlines()

        for line_num, line in enumerate(self.file_contents):
            line_anchors = re.findall(r'{{.*}}', line)
            for anchor in line_anchors:
                clean_anchor = anchor.strip('{} ').split('::')
                if clean_anchor[0].strip().lower() == 'file':
                    self.template_references[os.path.normcase(clean_anchor[1].strip(' \\/'))] = anchor
                elif clean_anchor[0].strip().lower() == 'value':
                    self.file_contents[line_num] = line.replace(anchor, template_values[clean_anchor[1].strip()])


def convert_markdown(source, target):
    """Convert markdown files (.md) in source to HTML and push to target in order to leave source clean.

    :param source:
    :param target:
    :return:
    """

    for (path, folders, filenames) in os.walk(source):
        for file in filenames:
            if len(file) > 2 and file[-3:] == '.md':
                path_name = os.path.normcase(os.path.join(path[len(source):], file).strip(' \\/'))
                with open(os.path.join(source, path_name), 'r') as i:
                    text = i.read()
                html = markdown.markdown(text)
                output_file = os.path.join(target, path_name[:-3]) + '.html'
                output_folder = os.path.split(output_file)[0]
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
                with open(output_file, 'w',
                          encoding='utf-8') as o:  # , errors='xmlcharrefreplace') as o:
                    o.write(html)


def load_dictionaries(folder):
    """Loads all yaml files in a given folder and its sub-folders into a single dictionary.
    Last version of a key loaded wins.

    """
    # Loads all yaml files in the target folder and its sub-folders.
    print(folder)
    dictionary = {}
    for (path, folders, filenames) in os.walk(folder):
        for file in filenames:
            if file[-4:] == '.yml' or file[-5:] == '.yaml':
                path_name = os.path.normcase(os.path.join(path[len(folder):], file).strip(' \\/'))
                with open(os.path.join(folder, path_name), 'r') as tv:
                    dictionary |= yaml.safe_load(tv)  # Merge dictionaries - last file loaded wins if key conflict.
    return dictionary


def load_files(source, target, dictionary):
    """Currently does three things that maybe should be split up:
    1. Loads files in source
    2. Loads files in target (files processed before the template substitution such as from Markdown compilation)
    3. Separates into files with vs without template refs, and files without refs into text vs binaries.
        TODO: there may be a crash currently if a binary file is used as a ref target.

    :param source: where site source is loaded from
    :param target: where compiled site is dumped
    :param dictionary: replacement values from the yaml files
    :return has_refs: list of files with template references to resolve
    :return no_refs: list of files with no template references to resolve
    """

    has_refs = {}
    no_refs = {}

    # TODO: move this and the below block to own function, pass in folder, dictionary,
    # TODO: binaries extensions, files to exclude from copying
    # TODO: or, could whitelist extensions to process instead of the binaries blacklist
    # TODO: these could be in a dictionary yaml file for easier config
    # load files in source and sort into lists for text with template refs, text without refs, and binaries:
    for (path, folders, filenames) in os.walk(source):
        for file in filenames:
            if file[-1] == '~' or file[-4:] == '.swp' or file[-3:] == '.md':
                continue  # skip vim temp files
            path_name = os.path.normcase(os.path.join(path[len(source):], file).strip(' \\/'))
            if file[-4:].lower() in ['.jpg', '.png', '.gif', 'tiff', '.ico']:
                # Binaries: copy to output but don't process.
                no_refs[path_name] = BinaryFile(source, path_name)
            else:
                # Text files are split into ones with {{ }} template refs in them (branches) and ones without (leaves).
                template_file = TemplateFile(source, path_name, dictionary)
                if len(template_file.template_references.keys()) > 0:
                    has_refs[path_name] = template_file
                else:
                    no_refs[path_name] = template_file

    # TODO: this is a near-duplicate of the source walk above. May be able to trim down or consolidate the two.
    # TODO: why is this duplicated? The only difference is the target folder and that it excludes .md files.
    # TODO: I can't remember why exactly we needed to compiles template refs in both source and target,
    # TODO: but this can be generalized with a flag or list of file extensions to include or exclude.
    for (path, folders, filenames) in os.walk(target):
        for file in filenames:
            if file[-1] == '~' or file[-4:] == '.swp':  # or file[-3:] == '.md':
                continue  # skip vim temp files
            path_name = os.path.normcase(os.path.join(path[len(target):], file).strip(' \\/'))
            if file[-4:].lower() in ['.jpg', '.png', '.gif', 'tiff', '.ico']:
                no_refs[path_name] = BinaryFile(target, path_name)
            else:
                template_file = TemplateFile(target, path_name, dictionary)
                if len(template_file.template_references.keys()) > 0:
                    has_refs[path_name] = template_file
                else:
                    no_refs[path_name] = template_file

    return has_refs, no_refs


def expand_templates(source, target, template_file):
    """Replace template refs {{ }} with their target contents, beginning with ones whose target has no refs itself.
    Collapses the reference tree starting at the leaves. Detects circularity (not a tree!) and errors out in that case.

    :param source:
    :param target:
    :param template_file:
    :return:
    """

    has_refs, no_refs = load_files(source, target, template_file)

    # TODO: silence this except when a debug flag is set
    print('\nhas references')
    for file in has_refs.keys():
        print(file)

    print('\nno references')
    for file in no_refs.keys():
        print(file)

    # TODO: was this here for a reason?
    #    for file in no_refs.keys():
    #        no_refs[file]

    # Replace refs with their contents if the target reference is in no_refs, meaning we're on a "leaf" of the
    # dependency tree.
    # If nothing changes on a pass, we're stuck due to circularity / orphans.
    ref_count_last = -1  # Unmatchable value, so we don't think we're stuck in a loop on first entry.
    while len(has_refs.keys()) > 0:
        ref_keys = []
        ref_keys.extend(has_refs.keys())

        if len(ref_keys) == ref_count_last:
            print('Circular or missing reference!')
            print(ref_keys)
            break

        ref_count_last = len(ref_keys)

        for file in ref_keys:
            template_ref_keys = []
            template_ref_keys.extend(has_refs[file].template_references.keys())
            for reference in template_ref_keys:
                if reference in no_refs:
                    # Inline that file's contents here
                    for n, line in enumerate(has_refs[file].file_contents):
                        has_refs[file].file_contents[n] = line.replace(has_refs[file].template_references[reference],
                                                                       ''.join(no_refs[reference].file_contents))
                    del has_refs[file].template_references[reference]
            if len(has_refs[file].template_references.keys()) == 0:
                no_refs[file] = has_refs[file]
                del has_refs[file]

    # Copy files to output folder. TODO: move to own function.
    for file in no_refs.keys():
        file_path = os.path.join(target, file)
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))
        if isinstance(no_refs[file], BinaryFile):
            with open(file_path, 'wb') as f:
                f.write(no_refs[file].file_contents)
        else:
            with open(file_path, 'w') as f:
                f.writelines(no_refs[file].file_contents)


def in_directory(file, directory):
    """Yoinked from a SO answer. Tests if (file) is a subpath of (directory).
    Does not check for actual file existence.

    """
    # make both absolute
    directory = os.path.join(os.path.realpath(directory), '')
    file = os.path.realpath(file)

    # return true, if the common prefix of both is equal to directory
    # e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
    return os.path.commonprefix([file, directory]) == directory


def clear_subfolder(folder):
    """Delete EVERYTHING in a folder, including sub-folders and their contents.
    Safety-checked to only remove folders that are sub-folders of the current working dir.
    :param folder: target folder to delete contents of.
    :return: none

    """
    if in_directory(folder, os.getcwd()):
        for root, dirs, files in os.walk(folder):
            for file in files:
                os.remove(os.path.join(root, file))
    else:
        print(f"{folder} not safe to remove! Must be a sub-folder of this program's location")


if __name__ == '__main__':
    """Normally run directly from command line. 
    Takes in optional command line args to change source and target.
    Target build folder is required to be a sub-folder of the program's folder
    for safety since all folders and files in it are destroyed each time.
    
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    args = parser.parse_args()
    site_folder = os.path.join(os.getcwd(), args.target)
    source_folder = os.path.join(site_folder, 'source')
    build_folder = os.path.join(site_folder, 'build')
    dictionary_folder = os.path.join(site_folder, 'dictionary')

    clear_subfolder(build_folder)  # prevents files removed in source from sticking around forever in the output
    dictionaries = load_dictionaries(dictionary_folder)
    print(dictionaries)
    convert_markdown(source_folder, build_folder)
    expand_templates(source_folder, build_folder, dictionaries)

    print('\nDone!')
