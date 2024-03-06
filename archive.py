#!/usr/bin/env python3
import re
import os
import argparse
from urllib.request import urlretrieve
from urllib.parse import urlparse, quote, unquote
from urllib.error import HTTPError, URLError

# example usage:
# python archive.py --page original-wiki-page.md --file-dir files --output readme.md --repo-base https://raw.githubusercontent.com/yuzu-mirror/yuzu-mod-archive/main

# group 1: game name
# group 2: contents
SECTION_REGEX = r"### ([A-Za-z0-9].+)((?:.|\n)*?)#"

# group 1: title
# group 2: link (raw)
# group 3: description
# group 4: version
# group 5: authors
# The contents of all groups, except the link group (2), may be formatted with Markdown.
TABLE_REGEX = r"\| \[(.+?)\]\((http.+?)\) *\| *(.+?) *\| *`(.+)` \| (.+)"

parser = argparse.ArgumentParser()
parser.add_argument("--page", required=True, help="path to the 'Switch Mods' wiki page Markdown file")
parser.add_argument("--file-dir", required=True, help="path to the directory to download all files to")
parser.add_argument("--output", required=True, help="filename of the output modified Markdown file, with replaced URLs")
parser.add_argument("--repo-base", required=True, help="base URL of the repository where the files will be held")
parser.add_argument("--no-dl", action="store_true", help="don't download anything, just output the modified document")
args = parser.parse_args()

with open(args.page, "r") as file:
    wiki_content = file.read()
    sections = re.findall(SECTION_REGEX, wiki_content)

replacements: list[tuple[str, str]] = []

def filter_name(s: str):
    return "".join([x for x in s if (x.isalnum() or x.isspace()) and (x != "\r" and x != "\n")])

for section in sections:
    game_name: str = section[0]
    table = section[1]

    folder_name = filter_name(game_name)
    folder = os.path.join(args.file_dir, folder_name)

    skip_dl = args.no_dl

    if not args.no_dl:
        if os.path.isdir(folder):
            print(f"[!] folder '{folder}' already exists, will skip dl'ing for this game")
            skip_dl = True
        else:
            os.makedirs(folder)

    for row in re.findall(TABLE_REGEX, table):
        title = row[0]
        url = row[1]
        description = row[2]
        version = row[3]
        authors = row[4]

        filename = unquote(os.path.basename(urlparse(url).path))

        out_url = f"{args.repo_base}/{args.file_dir}/{quote(folder_name)}/{quote(filename)}"

        if skip_dl:
            replacements.append((url, out_url))
            continue

        try:
            urlretrieve(url, os.path.join(folder, filename))
            print(f"[+] mod '{title}' downloaded for game {game_name}")
            replacements.append((url, out_url))
        except HTTPError as e:
            print(f"[ ] mod '{title}' not available from original source, error {e}")

            # try using the internet archive
            try:
                # the date does not matter, IA will automatically pick the closest one (we use the oldest date
                # available so that we don't download an archived error message)
                #
                # this assumes the files itself don't change, which is true for the mods that we need to archive
                webarchive_url = f"https://web.archive.org/web/20200101125317if_/{url}"
                urlretrieve(webarchive_url, os.path.join(folder, filename))
                print(f"[+]    mod downloaded from the Internet Archive")
                replacements.append((url, out_url))
            except:
                print(f"[-] mod not available on the Internet Archive nor the original source")
        except URLError as e:
            print(f"[-] mod '{title}' NOT downloaded - URL error {e}")
            print(f"    url: {url}")

        
modified = wiki_content
for item in replacements:
    modified = modified.replace(item[0], item[1])

with open(args.output, "w") as file:
    file.write(modified)

print(f"[+] all done! modified document saved to '{args.output}'")
