#!/usr/bin/python3
# Helper script to create and publish a new python-chess release.

import os
import chess
import sys
import zipfile
import textwrap
import configparser
import requests
import bs4


def system(command):
    print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        sys.exit(exit_code)


def check_git():
    print("--- CHECK GIT ----------------------------------------------------")
    system("git diff --exit-code")
    system("git diff --cached --exit-code")


def test():
    print("--- TEST ---------------------------------------------------------")
    system("tox --skip-missing-interpreters")


def check_changelog():
    print("--- CHECK CHANGELOG ----------------------------------------------")
    with open("CHANGELOG.rst", "r") as changelog_file:
        changelog = changelog_file.read()

    if "Upcoming in the next release" in changelog:
        print("Found: Upcoming in the next release")
        sys.exit(1)

    tagname = "v{0}".format(chess.__version__)
    if tagname not in changelog:
        print("Not found: {0}".format(tagname))
        sys.exit(1)


def check_docs():
    print("--- CHECK DOCS ---------------------------------------------------")
    system("python3 setup.py --long-description | rst2html --strict --no-raw > /dev/null")


def tag_and_push():
    print("--- TAG AND PUSH -------------------------------------------------")
    tagname = "v{0}".format(chess.__version__)
    release_filename = "release-{0}.txt".format(tagname)

    if not os.path.exists(release_filename):
        print(">>> Creating {0} ...".format(release_filename))
        first_section = False
        prev_line = None
        with open(release_filename, "w") as release_txt, open("CHANGELOG.rst", "r") as changelog_file:
            headline = "python-chess {0}".format(tagname)
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
        print("Actual tagname is: {0}".format(tagname))
        sys.exit(1)

    system("git tag {0} -s -F {1}".format(tagname, release_filename))
    system("git push origin master {0}".format(tagname))
    return tagname


def update_rtd():
    print("--- UPDATE RTD ---------------------------------------------------")
    system("curl -X POST http://readthedocs.org/build/python-chess")


def pypi():
    print("--- PYPI ---------------------------------------------------------")
    system("python3 setup.py sdist upload")


def pythonhosted(tagname):
    print("--- PYTHONHOSTED -------------------------------------------------")

    print("Creating pythonhosted.zip ...")
    with zipfile.ZipFile("pythonhosted.zip", "w") as zip_file:
        zip_file.writestr("index.html", textwrap.dedent("""\
            <html>
              <head>
                <meta http-equiv="refresh" content="0;url=http://python-chess.readthedocs.io/en/{0}/">
                <script>
                  window.location.href = 'http://python-chess.readthedocs.io/en/{0}/';
                </script>
              </head>
            </html>""".format(tagname)))

    print("Getting credentials ...")
    config = configparser.ConfigParser()
    config.read(os.path.expanduser("~/.pypirc"))
    username = config.get("pypi", "username")
    password = config.get("pypi", "password")
    auth = requests.auth.HTTPBasicAuth(username, password)
    print("Username: {0}".format(username))

    print("Getting CSRF token ...")
    session = requests.Session()
    res = session.get("https://pypi.python.org/pypi?:action=pkg_edit&name=python-chess", auth=auth)
    if res.status_code != 200:
        print(res.text)
        print(res)
        sys.exit(1)
    soup = bs4.BeautifulSoup(res.text, "html.parser")
    csrf = soup.find("input", {"name": "CSRFToken"})["value"]
    print("CSRF: {0}".format(csrf))

    print("Uploading ...")
    with open("pythonhosted.zip", "rb") as zip_file:
        res = session.post("https://pypi.python.org/pypi", auth=auth, data={
            "CSRFToken": csrf,
            ":action": "doc_upload",
            "name": "python-chess",
        }, files={
            "content": zip_file,
        })
    if res.status_code != 200 or tagname not in res.text:
        print(res.text)
        print(res)
        sys.exit(1)

    print("Done.")


def github_release(tagname):
    print("--- GITHUB RELEASE -----------------------------------------------")
    print("https://github.com/niklasf/python-chess/releases/new?tag={0}".format(tagname))


if __name__ == "__main__":
    test()
    check_docs()
    check_changelog()
    check_git()
    tagname = tag_and_push()
    update_rtd()
    pypi()
    pythonhosted(tagname)
    github_release(tagname)
