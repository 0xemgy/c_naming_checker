import clang.cindex
from tabulate import tabulate
import os

# Set the path to the Clang library for Windows (libclang.dll)
clang.cindex.Config.set_library_file(r"C:\LLVM\bin\libclang.dll")

# Initialize the Clang index
index = clang.cindex.Index.create()

# Parse the C file
c_file_name = r"C:\work\repos\motor_control_ecu\src\bsw\main.h"
translation_unit = index.parse(c_file_name, options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)

# List to hold findings
findings = []

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
                'typedef_base': ''
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
                'typedef_base': ''
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
                        'typedef_base': ''
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
                'typedef_base': ''
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
                        'typedef_base': ''
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
                'typedef_base': node.underlying_typedef_type.spelling.split()[-1]
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
                'typedef_base': ''
            })
            for param in node.get_arguments():
                findings.append({
                    'name': param.spelling,
                    'file': node.location.file.name,
                    'line': node.location.line,
                    'column': node.location.column,
                    'kind': 'Parameter',
                    'enum_type': '',
                    'typedef_base': ''
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
                'typedef_base': ''
            })
    
    # Recurse through child nodes
    if node.kind != clang.cindex.CursorKind.TYPEDEF_DECL:
        for child in node.get_children():
            visit_node(child, file_name, depth + 1)

# Visit the root node (TranslationUnit) and traverse its children
visit_node(translation_unit.cursor, c_file_name)

# Print the findings in a nicely formatted table
print(tabulate(findings, headers="keys", tablefmt="simple"))
