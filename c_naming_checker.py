import clang.cindex
from tabulate import tabulate
import os
import re

# Set the path to the Clang library for Windows (libclang.dll)
clang.cindex.Config.set_library_file(r"C:\LLVM\bin\libclang.dll")

# Initialize the Clang index
index = clang.cindex.Index.create()

# Parse the C file
c_file_name = r"C:\work\repos\motor_control_ecu\src\bsw\main.c"
translation_unit = index.parse(c_file_name, options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)

# List to hold findings
findings = []

# Function to detect case of identifiers
def detect_case(identifier):
    if re.match(r'^[a-z0-9]+(_[a-z0-9]+)*$', identifier):
        return 'snake_case'
    elif re.match(r'^[A-Z0-9]+(_[A-Z0-9]+)*$', identifier):
        return 'SNAKE_CASE'
    else:
        return 'invalid'

# Function to check if the identifier is prefixed with the base file name
def is_prefixed_with_filename(identifier, file_name):
    base_name = os.path.splitext(os.path.basename(file_name))[0]
    
    # Check if the identifier starts with the base name, in either lower case or upper case (for snake_case or SNAKE_CASE)
    if identifier.startswith(base_name.lower() + "_") or identifier.startswith(base_name.upper() + "_"):
        return True
    return False

def visit_node(node, file_name, depth=0):
    file_extension = os.path.splitext(file_name)[1]

    # Check if the declaration/definition is from the current file and not from headers
    if node.location.file and node.location.file.name == file_name:
        # Determine the visibility based on file type and static keyword
        is_header = file_extension == '.h'

        if node.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
            kind = 'Global Define' if is_header else 'Define'
            findings.append({
                'name': node.spelling,
                'file': node.location.file.name,
                'line': node.location.line,
                'column': node.location.column,
                'kind': kind,
                'enum_type': '',
                'typedef_base': '',
                'case': detect_case(node.spelling),
                'is_prefixed': is_prefixed_with_filename(node.spelling, file_name)
            })
        
        elif node.kind == clang.cindex.CursorKind.STRUCT_DECL:
            kind = 'Global Struct' if is_header else 'Local Struct'
            findings.append({
                'name': node.spelling,
                'file': node.location.file.name,
                'line': node.location.line,
                'column': node.location.column,
                'kind': kind,
                'enum_type': '',
                'typedef_base': '',
                'case': detect_case(node.spelling),
                'is_prefixed': is_prefixed_with_filename(node.spelling, file_name)
            })
            for child in node.get_children():
                if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                    findings.append({
                        'name': child.spelling,
                        'file': node.location.file.name,
                        'line': node.location.line,
                        'column': node.location.column,
                        'kind': 'Member Variable',
                        'enum_type': '',
                        'typedef_base': '',
                        'case': detect_case(child.spelling),
                        'is_prefixed': is_prefixed_with_filename(child.spelling, file_name)
                    })
        
        elif node.kind == clang.cindex.CursorKind.ENUM_DECL:
            kind = 'Global Enum' if is_header else 'Local Enum'
            findings.append({
                'name': node.spelling,
                'file': node.location.file.name,
                'line': node.location.line,
                'column': node.location.column,
                'kind': kind,
                'enum_type': '',
                'typedef_base': '',
                'case': detect_case(node.spelling),
                'is_prefixed': is_prefixed_with_filename(node.spelling, file_name)
            })
            for child in node.get_children():
                if child.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL:
                    kind = 'Global Enum Value' if is_header else 'Local Enum Value'
                    findings.append({
                        'name': child.spelling,
                        'file': node.location.file.name,
                        'line': node.location.line,
                        'column': node.location.column,
                        'kind': kind,
                        'enum_type': node.spelling,
                        'typedef_base': '',
                        'case': detect_case(child.spelling),
                        'is_prefixed': is_prefixed_with_filename(child.spelling, file_name)
                    })
        
        elif node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            kind = 'Global Typedef' if is_header else 'Local Typedef'
            findings.append({
                'name': node.spelling,
                'file': node.location.file.name,
                'line': node.location.line,
                'column': node.location.column,
                'kind': kind,
                'enum_type': '',
                'typedef_base': node.underlying_typedef_type.spelling.split()[-1],
                'case': detect_case(node.spelling),
                'is_prefixed': is_prefixed_with_filename(node.spelling, file_name)
            })
        
        elif node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            if is_header or node.storage_class == clang.cindex.StorageClass.EXTERN:
                kind = 'Global Function'
            else:
                kind = 'Local Function'

            findings.append({
                'name': node.spelling,
                'file': node.location.file.name,
                'line': node.location.line,
                'column': node.location.column,
                'kind': kind,
                'enum_type': '',
                'typedef_base': '',
                'case': detect_case(node.spelling),
                'is_prefixed': is_prefixed_with_filename(node.spelling, file_name)
            })
            for param in node.get_arguments():
                findings.append({
                    'name': param.spelling,
                    'file': node.location.file.name,
                    'line': node.location.line,
                    'column': node.location.column,
                    'kind': 'Parameter',
                    'enum_type': '',
                    'typedef_base': '',
                    'case': detect_case(param.spelling),
                    'is_prefixed': is_prefixed_with_filename(param.spelling, file_name)
                })
        
        elif node.kind == clang.cindex.CursorKind.VAR_DECL:
            if is_header or node.storage_class == clang.cindex.StorageClass.EXTERN:
                kind = 'Global Variable'
            else:
                if node.storage_class == clang.cindex.StorageClass.STATIC:
                    kind = 'Local Variable'
                else:
                    kind = 'Auto Variable'
            findings.append({
                'name': node.spelling,
                'file': node.location.file.name,
                'line': node.location.line,
                'column': node.location.column,
                'kind': kind,
                'enum_type': '',
                'typedef_base': '',
                'case': detect_case(node.spelling),
                'is_prefixed': is_prefixed_with_filename(node.spelling, file_name)
            })
    
    # Recurse through child nodes
    if node.kind != clang.cindex.CursorKind.TYPEDEF_DECL:
        for child in node.get_children():
            visit_node(child, file_name, depth + 1)

# Visit the root node (TranslationUnit) and traverse its children
visit_node(translation_unit.cursor, c_file_name)

# Print the findings in a nicely formatted table
print(tabulate(findings, headers="keys", tablefmt="simple"))
