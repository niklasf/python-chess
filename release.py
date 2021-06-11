#!/usr/bin/python3
# Helper script to create and publish a new python-chess release.

import os
import chess
import sys
import subprocess


def system(command):
    print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        sys.exit(exit_code)


def check_git():
    print("--- CHECK GIT ----------------------------------------------------")
    system("git diff --exit-code")
    system("git diff --cached --exit-code")

    system("git fetch origin")
    behind = int(subprocess.check_output(["git", "rev-list", "--count", "master..origin/master"]))
    if behind > 0:
        print(f"master is {behind} commit(s) behind origin/master")
        sys.exit(1)


def test():
    print("--- TEST ---------------------------------------------------------")
    system("tox --skip-missing-interpreters")


def check_changelog():
    print("--- CHECK CHANGELOG ----------------------------------------------")
    with open("CHANGELOG.rst", "r") as changelog_file:
        changelog = changelog_file.read()

    if "Upcoming in" in changelog:
        print("Found: Upcoming in")
        sys.exit(1)

    tagname = f"v{chess.__version__}"
    if tagname not in changelog:
        print(f"Not found: {tagname}")
        sys.exit(1)


def check_docs():
    print("--- CHECK DOCS ---------------------------------------------------")
    system("python3 setup.py --long-description | rst2html --strict --no-raw > /dev/null")


def tag_and_push():
    print("--- TAG AND PUSH -------------------------------------------------")
    tagname = f"v{chess.__version__}"
    release_filename = f"release-{tagname}.txt"

    if not os.path.exists(release_filename):
        print(f">>> Creating {release_filename} ...")
        first_section = False
        prev_line = None
        with open(release_filename, "w") as release_txt, open("CHANGELOG.rst", "r") as changelog_file:
            headline = f"python-chess {tagname}"
            release_txt.write(headline + os.linesep)

            for line in changelog_file:
                if not first_section:
                    if line.startswith("-------"):
                        first_section = True
                else:
                    if line.startswith("-------"):
                        break
                    else:
                        if not prev_line.startswith("------"):
                            release_txt.write(prev_line)

                prev_line = line

    with open(release_filename, "r") as release_txt:
        release = release_txt.read().strip() + os.linesep
        print(release)

    with open(release_filename, "w") as release_txt:
        release_txt.write(release)

    guessed_tagname = input(">>> Sure? Confirm tagname: ")
    if guessed_tagname != tagname:
        print(f"Actual tagname is: {tagname}")
        sys.exit(1)

    system(f"git tag {tagname} -s -F {release_filename}")
    system(f"git push --atomic origin master {tagname}")
    return tagname


def pypi():
    print("--- PYPI ---------------------------------------------------------")
    system("rm -rf build")
    system("python3 setup.py sdist bdist_wheel")
    system("twine check dist/*")
    system("twine upload --skip-existing --sign dist/*")


def github_release(tagname):
    print("--- GITHUB RELEASE -----------------------------------------------")
    print(f"https://github.com/niklasf/python-chess/releases/new?tag={tagname}")


if __name__ == "__main__":
    check_docs()
    test()
    check_git()
    check_changelog()
    tagname = tag_and_push()
    pypi()
    github_release(tagname)
