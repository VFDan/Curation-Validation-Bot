import os
import shutil
import json
import re
from typing import List, Tuple

def validate_curation(filename: str) -> Tuple[List, List]:
    errors: List = []
    warnings: List = []

    # process archive
    archive = py7zr.SevenZipFile(filename, mode='r')
    filenames = archive.getnames()
    archive.extractall()
    archive.close()

    # check files
    uuid_folder_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    content_folder_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/content$")
    meta_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\/meta\.(yaml|yml|txt)$")
    logo_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\/logo\.(png)$")
    ss_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\/ss\.(png)$")
    uuid_folder = [match for match in filenames if uuid_folder_regex.match(match) is not None]
    content_folder = [match for match in filenames if content_folder_regex.match(match) is not None]
    meta = [match for match in filenames if meta_regex.match(match) is not None]
    logo = [match for match in filenames if logo_regex.match(match) is not None]
    ss = [match for match in filenames if ss_regex.match(match) is not None]

    props: dict = {}
    if not uuid_folder:
        errors.append("Root folder format is invalid. It should be a UUIDv4.")
    if not content_folder:
        errors.append("Content folder not found.")
    if not logo:
        errors.append("Logo file is either missing or its filename is incorrect.")
    if not ss:
        errors.append("Screenshot file is either missing or its filename is incorrect.")

    # process meta
    if not meta:
        errors.append("Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?")
    else:
        meta_filename = meta[0]
        with open(meta_filename) as meta_file:
            if meta_filename.endswith(".yml") or meta_filename.endswith(".yaml"):
                try:
                    props: dict = yaml.safe_load(meta_file)
                except yaml.YAMLError:  # If this is being called, it's a meta .txt
                    errors.append("Unable to load meta YAML file")
            elif meta_filename.endswith(".txt"):
                break_index: int = 0
                while break_index != -1:
                    props, break_index = parse_lines_until_multiline(meta_file.readlines(), props,
                                                                    break_index)
                    props, break_index = parse_multiline(meta_file.readlines(), props, break_index)
            else:
                errors.append("Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?")

        # TODO replace these string boolifications with something more sensible
        title: tuple[str, bool] = ("Title", bool(props["Title"]))
        # developer: tuple[str, bool] = ("Developer", bool(props["Developer"]))

        release_date: tuple[str, bool] = ("Release Date", bool(props["Release Date"]))
        if release_date[1]:
            date_string = props["Release Date"]
            regex = re.compile(r"^\d{4}-\d{2}-\d{2}$")
            if not regex.match(date_string):
                errors.append("Release date is incorrect. Release dates should always be in `YYYY-MM-DD` format.")

        language_properties: tuple[str, bool] = ("Languages", bool(props["Languages"]))
        if language_properties[1]:
            with open("language-codes.json") as f:
                list_of_language_codes: list[dict] = json.load(f)
                language_str: str = props["Languages"]
                languages = language_str.split(";")
                languages = [x.strip(' ') for x in languages]
                language_codes = []
                for x in list_of_language_codes:
                    language_codes.append(x["alpha2"])
                for language in languages:
                    if language not in language_codes:
                        if language == "sp":
                            errors.append("The correct ISO 639-1 language code for Spanish is `es`, not `sp`.")
                        elif language == "ge":
                            errors.append("The correct ISO 639-1 language code for German is `de`, not `ge`.")
                        elif language == "jp":
                            errors.append("The correct ISO 639-1 language code for Japanese is `ja`, not `jp`.")
                        elif language == "kr":
                            errors.append("The correct ISO 639-1 language code for Korean is `ko`, not `kr`.")
                        elif language == "ch":
                            errors.append("The correct ISO 639-1 language code for Chinese is `zh`, not `ch`.")
                        elif language == "iw":
                            errors.append("The correct ISO 639-1 language code for Hebrew is `he`, not `iw`.")
                        elif language == "cz":
                            errors.append("The correct ISO 639-1 language code for Czech is `cs`, not `cz`.")
                        elif language == "pe":
                            errors.append("The correct ISO 639-1 language code for Farsi is `fa`, not `pe`.")
                        else:
                            errors.append(f"Code `{language}` is not a valid ISO 639-1 language code.")

        tag: Tuple[str, bool] = ("Tags", bool(props["Tags"]))
        source: Tuple[str, bool] = ("Source", bool(props["Source"]))
        status: Tuple[str, bool] = ("Status", bool(props["Status"]))
        launch_command: Tuple[str, bool] = ("Launch Command", bool(props["Launch Command"]))
        application_path: Tuple[str, bool] = ("Application Path", bool(props["Application Path"]))

        # TODO check description?
        # description: Tuple[str, bool] = ("Description", bool(props["Original Description"]))
        # if description[1] is False and (
        #         bool(props["Curation Notes"]) or bool(props["Game Notes"])):
        #     reply += "Make sure you didn't put your description in the notes section.\n"

        if "https" in props["Launch Command"]:
            errors.append("Found `https` in launch command. All launch commands must use `http` instead of `https`.")
        mandatory_props: List[Tuple[str, bool]] = [title, language_properties, source, launch_command, tag, status, application_path]

        # TODO check optional props?
        # optional_props: list[tuple[str, bool]] = [developer, release_date, tag, description]
        # if not all(optional_props[1]): for x in optional_props: if x[1] is False: reply += x[0] +
        # "is missing, but not necessary. Add it if you can find it, but it's okay if you can't.\n"

        tags: List[str] = props["Tags"].split(";")
        tags: List[str] = [x.strip(' ') for x in tags]
        with open('tags.txt') as file:
            contents = file.read()
            for tag in tags:
                if tag not in contents:
                    warnings.append(f"Tag `{tag}` is not a known tag.")
        if not all(mandatory_props[1]):
            for prop in mandatory_props:
                if prop[1] is False:
                    errors.append(f"Property `{prop[0]}` is missing.")

    for filename in filenames:
        shutil.rmtree(filename, True)

    return errors, warnings