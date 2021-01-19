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
    size_special = {
        -1: 'symlink',
        -2: 'error_file_or_folder_not_found'
    }
    if size_in_bytes in size_special:
        return size_special[size_in_bytes]
    else:
        power = 1
        size = size_in_bytes
        while size > 1024:
            size = size / 1024
            power += 1
            if power >= 6:
                break
        return "{} {}".format(round(size, ndigits=ndigits), power_to_unit[power])


def make_table_list(item_list, size_list, mod_time_list=None):
    table = []
    # checks
    if len(item_list) == len(size_list):
        # check if mod_times present and ok
        if mod_time_list is not None and len(item_list) == len(mod_time_list):
            table = ["Name", "Size", "Last modified"]
            for file, size, mod_time in zip(item_list, size_list, mod_time_list):
                table.extend([file, human_readable_size_as_string(size), mod_time])
        else:
            table = ["Name", "Size"]
            for folder, size in zip(item_list, size_list):
                table.extend([folder, human_readable_size_as_string(size)])
    return table


def get_mod_time_list_files(file_list, path_to_files):
    mod_times = []
    for file in file_list:
        fp = os.path.join(path_to_files, file)
        if not os.path.isfile(fp):
            mod_times.append("file_not_found")
        elif os.path.islink(fp):
            mod_times.append("symlink")
        else:
            mod_times.append(time.ctime(os.path.getmtime(fp)))
    return mod_times


def get_size_list_files(file_list, path_to_files):
    sizes = []
    for file in file_list:
        fp = os.path.join(path_to_files, file)
        if not os.path.isfile(fp):
            # -2 -> file_not_found
            sizes.append(-2)
        elif os.path.islink(fp):
            # -1 -> symlink
            sizes.append(-1)
        else:
            sizes.append(os.path.getsize(fp))
    return sizes


def get_size_list_folders(folder_list, path_to_folders, input_dict):
    sizes = []
    for folder in folder_list:
        fp = os.path.join(path_to_folders, folder)
        if os.path.islink(fp):
            sizes.append(-1)
        elif fp in input_dict:
            sizes.append(input_dict[fp]["Size"])
        else:
            sizes.append(-2)
    return sizes


def gen_markdown_folder_section(md_report_file, use_dict, path):
    md_report_file.new_paragraph("This folder contains {} files and {} sub-folders.".format(
        use_dict["Number of files"], use_dict["Number of sub-folders"]))
    md_report_file.new_line("Total size in bytes: {}".format(use_dict["Size"]))
    md_report_file.new_line("Total size: {}".format(human_readable_size_as_string(use_dict["Size"])))
    md_report_file.new_line()
    if use_dict["Number of files"] > 0:
        md_report_file.new_header(level=2, title="Files")
        md_report_file.new_table(columns=3, rows=1 + use_dict["Number of files"],
                                 text=make_table_list(item_list=use_dict["Files in folder"],
                                                      size_list=use_dict["file_sizes"],
                                                      mod_time_list=use_dict["file_mod_times"]))
        md_report_file.new_line()
    if use_dict["Number of sub-folders"] > 0:
        md_report_file.new_header(level=2, title="Folders")
        md_report_file.new_table(columns=2, rows=1 + use_dict["Number of sub-folders"],
                                 text=make_table_list(item_list=use_dict["Sub-folders"],
                                                      size_list=use_dict["sub-folder_sizes"]))
        md_report_file.new_line()


def make_markdown_report(in_data_dict, out_folder, base_folder, level_cap=None):
    md_report_file = MdUtils(file_name=os.path.join(out_folder, 'Data_Report.md'),
                             title='Storage Report on {}'.format(base_folder))
    md_report_file.new_paragraph("This is an auto-generated storage report giving detailed info on files and folders "
                                 "inside base the folder.")
    md_report_file.new_line("Report generated {}".format(datetime.now().strftime("%d.%m.%Y %H:%M:%S")))
    if level_cap is None or level_cap > in_data_dict["max_depth"]:
        level_cap = in_data_dict["max_depth"]
    else:
        md_report_file.new_line("Report generation was limited to folder level {}".format(level_cap))
    for i in range(0, level_cap+1):
        for key, item in in_data_dict[i].items():
            if i == 0:
                md_report_file.new_header(level=1, title='Content of the base folder {}'.format(key))
            else:
                md_report_file.new_header(level=1, title='Content of Sub-Folder level {}: {} '.format(i, key))
            gen_markdown_folder_section(md_report_file, item, key)
    md_report_file.new_table_of_contents(table_title='Contents', depth=1)
    md_report_file.create_md_file()


def scan_folder(folder):
    data_report_dict = {}
    for current_d, dirs, files in os.walk(folder):
        if current_d == folder:
            data_report_dict[0] = {}
            data = data_report_dict[0]
            data_report_dict["max_depth"] = 0
        else:
            level = len(os.path.relpath(current_d, start=folder).split('/'))
            if not level in data_report_dict:
                data_report_dict[level] = {}
                if level > data_report_dict["max_depth"]:
                    data_report_dict["max_depth"] = level
            data = data_report_dict[level]
        data[current_d] = {}
        data = data[current_d]
        data["Number of sub-folders"] = len(dirs)
        data["Number of files"] = len(files)
        data["Size"] = get_folder_size(current_d)
        data["Files in folder"] = files
        data["Sub-folders"] = dirs
    # fill size info lists
    for i in range(0, data_report_dict["max_depth"]+1):
        for key, item in data_report_dict[i].items():
            if item["Number of files"] > 0:
                item["file_sizes"] = get_size_list_files(item["Files in folder"], key)
                item["file_mod_times"] = get_mod_time_list_files(item["Files in folder"], key)
            else:
                item["file_sizes"] = None
                item["file_mod_times"] = None
            if item["Number of sub-folders"] > 0 and i+1 in data_report_dict:
                item["sub-folder_sizes"] = get_size_list_folders(item["Sub-folders"], key, data_report_dict[i+1])
            else:
                item["sub-folder_sizes"] = None
    return data_report_dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="storage_report - simple folder content report generator (as markdown)")
    parser.add_argument("folder", help="base folder that shall be scanned")
    parser.add_argument("output_folder", help="output folder for generated files")
    parser.add_argument("--json", help="Generate a json file with folder info", action='store_true')
    parser.add_argument("--max_lvl_md", help="Limit markdown report to this sub-folder lvl", type=int, default=None)
    args = parser.parse_args()
    if not os.path.exists(args.folder):
        print('The folder {} does not exist - aborting'.format(args.folder))
        sys.exit(1)
    if not os.path.exists(args.output_folder):
        os.mkdir(args.output_folder)
    data_dict = scan_folder(args.folder)
    make_markdown_report(data_dict, args.output_folder, args.folder, args.max_lvl_md)
    if args.json:
        with open(os.path.join(args.output_folder, 'report.json'), 'w') as report_json:
            json.dump(data_dict, report_json, indent=4)
    print('Done')
    sys.exit(0)
