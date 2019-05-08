from json import dump, load
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool
from pathlib import Path
from subprocess import PIPE, Popen, run
from isort import SortImports
from autoflake import fix_code
from black import format_str, format_file_contents, FileMode, DEFAULT_LINE_LENGTH, PY36_VERSIONS

pool = Pool(cpu_count())


def clean_python_code(python_source, isort=True, black=True, autoflake=True):
    # run source code string through autoflake, isort, and black
    formatted_source = python_source

    if autoflake:
        formatted_source = fix_code(
            formatted_source,
            expand_star_imports=True,
            remove_all_unused_imports=True,
            remove_duplicate_keys=True,
            remove_unused_variables=True,
        )

    if isort:
        formatted_source = SortImports(file_contents=formatted_source).output

    if black:
        mode = FileMode(
            target_versions=PY36_VERSIONS,
            line_length=DEFAULT_LINE_LENGTH,
            is_pyi=False,
            string_normalization=True,
        )
        formatted_source = format_file_contents(
            formatted_source, fast=True, mode=mode)
    return formatted_source


def clear_ipynb_output(ipynb_file_path):
    # clear cell outputs, reset cell execution count of each cell in a jupyer notebook
    run(
        (
            "jupyter",
            "nbconvert",
            "--ClearOutputPreprocessor.enabled=True",
            "--inplace",
            ipynb_file_path,
        ),
        check=True,
    )


def clean_ipynb_cell(cell_dict):
    # clean a single cell within a jupyter notebook
    if cell_dict["cell_type"] == "code":
        clean_lines = clean_python_code(
            "".join(cell_dict["source"])).split("\n")

        if len(clean_lines) == 1 and clean_lines[0] == "":
            clean_lines = []
        else:
            clean_lines[:-1] = [clean_line +
                                "\n" for clean_line in clean_lines[:-1]]
        cell_dict["source"] = clean_lines
        return cell_dict
    else:
        return cell_dict


def clean_ipynb(
    ipynb_file_path, clear_output=True, autoflake=True, isort=True, black=True
):
    # load, clean and write .ipynb source in-place, back to original file
    if clear_output:
        clear_ipynb_output(ipynb_file_path)

    with open(ipynb_file_path) as ipynb_file:
        ipynb_dict = load(ipynb_file)

    # mulithread the map operation
    processed_cells = pool.map(clean_ipynb_cell, ipynb_dict["cells"])
    ipynb_dict["cells"] = processed_cells

    with open(ipynb_file_path, "w") as ipynb_file:
        dump(ipynb_dict, ipynb_file, indent=1)
        ipynb_file.write("\n")


def create_file(file_path, contents):
    file_path.touch()
    file_path.open("w", encoding="utf-8").write(contents)


def clean_py(py_file_path, autoflake=True, isort=True, black=True):
    # load, clean and write .py source, write cleaned file back to disk
    with open(py_file_path, "r") as file:
        source = file.read()

    clean_lines = clean_python_code("".join(source))
    create_file(Path(py_file_path), clean_lines)
