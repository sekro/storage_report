"""
Simple folder content report tool
Written for usage on HUNT cloud
Sebastian Krossa
sebastian.krossa@ntnu.no
NTNU, Trondheim, Norway Jan 2021
"""

import os
import json
import time
import argparse
import sys
from mdutils.mdutils import MdUtils
from datetime import datetime


def get_folder_size(folder):
    size = 0
    for current, dirs, files in os.walk(folder):
        if len(dirs) > 0:
            for d in dirs:
                size += get_folder_size(d)
        for file in files:
            file_path = os.path.join(current, file)
            if not os.path.islink(file_path):
                size += os.path.getsize(file_path)
    return size


def human_readable_size_as_string(size_in_bytes, ndigits=3):
    power_to_unit = {
        1: 'b',
        2: 'Kb',
        3: 'Mb',
        4: 'Gb',
        5: 'Tb',
        6: 'Pb'
    }
    power = 1
    size = size_in_bytes
    while size > 1024:
        size = size / 1024
        power += 1
        if power >= 6:
            break
    return "{} {}".format(round(size, ndigits=ndigits), power_to_unit[power])


def make_table_list(item_list, path=None, size_list=None):
    table = []
    if size_list is not None and len(item_list) == len(size_list):
        table = ["Name", "Total Size"]
        for folder, size in zip(item_list, size_list):
            table.extend([folder, human_readable_size_as_string(size)])
    elif path is not None:
        table = ["Name", "Size", "Last modified"]
        for file in item_list:
            fp = os.path.join(path, file)
            if not os.path.isfile(fp):
                size_str = "file_not_found"
                mod_time = "file_not_found"
            elif not os.path.islink(fp):
                size_str = human_readable_size_as_string(os.path.getsize(fp))
                mod_time = time.ctime(os.path.getmtime(fp))]
            else:
                size_str = "symlink"
                mod_time = "symlink"
            table.extend([file, size_str, mod_time])
    return table


def get_sizes(folder_list, path, input_dict):
    sizes = []
    for folder in folder_list:
        sizes.append(input_dict[os.path.join(path, folder)]["Size"])
    return sizes


def make_markdown_report(in_data_dict, out_folder, base_folder):
    md_report_file = MdUtils(file_name=os.path.join(out_folder, 'Data_Report.md'),
                             title='Storage Report on {}'.format(base_folder))
    md_report_file.new_paragraph("This is an auto-generated storage report giving detailed info on files and folders "
                                 "inside base the folder.")
    md_report_file.new_line("Report generated {}".format(datetime.now().strftime("%d.%m.%Y %H:%M:%S")))

    for key, item in in_data_dict.items():
        use_dict = None
        path = None
        if key == 'base':
            md_report_file.new_header(level=1, title='Content of the base folder {}'.format(item))
            use_dict = in_data_dict
            path = item
        elif isinstance(item, dict):
            md_report_file.new_header(level=1, title='Content of Sub-Folder {}'.format(key))
            use_dict = item
            path = key
        if use_dict is not None:
            md_report_file.new_paragraph("This folder contains {} files and {} sub-folders.".format(
                use_dict["Number of files"], use_dict["Number of sub-folders"]))
            md_report_file.new_line("Total size in bytes: {}".format(use_dict["Size"]))
            md_report_file.new_line("Total size: {}".format(human_readable_size_as_string(use_dict["Size"])))
            if use_dict["Number of files"] > 0:
                md_report_file.new_header(level=2, title="Files")
                md_report_file.new_table(columns=3, rows=1 + use_dict["Number of files"],
                                         text=make_table_list(item_list=use_dict["Files in folder"], path=path))
            if use_dict["Number of sub-folders"] > 0:
                md_report_file.new_header(level=2, title="Folders")
                md_report_file.new_table(columns=2, rows=1 + use_dict["Number of sub-folders"],
                                         text=make_table_list(item_list=use_dict["Sub-folders"],
                                                              size_list=get_sizes(use_dict["Sub-folders"],
                                                                                  path=path,
                                                                                  input_dict=in_data_dict)))

    md_report_file.new_table_of_contents(table_title='Contents', depth=2)
    md_report_file.create_md_file()


def scan_folder(folder):
    data_report_dict = {}
    for current_d, dirs, files in os.walk(folder):
        if current_d == folder:
            data_report_dict["base"] = folder
            data = data_report_dict
        else:
            data_report_dict[current_d] = {}
            data = data_report_dict[current_d]
        data["Number of sub-folders"] = len(dirs)
        data["Number of files"] = len(files)
        data["Size"] = get_folder_size(current_d)
        data["Files in folder"] = files
        data["Sub-folders"] = dirs
    return data_report_dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="storage_report - simple folder content report generator (as markdown)")
    parser.add_argument("folder", help="base folder that shall be scanned")
    parser.add_argument("output_folder", help="output folder for generated files")
    parser.add_argument("--json", help="Generate a json file with folder info", action='store_true')
    args = parser.parse_args()
    if not os.path.exists(args.folder):
        print('The folder {} does not exist - aborting'.format(args.folder))
        sys.exit(1)
    if not os.path.exists(args.output_folder):
        os.mkdir(args.output_folder)
    data_dict = scan_folder(args.folder)
    make_markdown_report(data_dict, args.output_folder, args.folder)
    if args.json:
        with open(os.path.join(args.output_folder, 'report.json'), 'w') as report_json:
            json.dump(data_dict, report_json, indent=4)
    print('Done')
    sys.exit(0)
