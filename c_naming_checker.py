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
    return identifier.startswith(base_name.lower() + "_") or identifier.startswith(base_name.upper() + "_")

# Function to check if the identifier is prefixed with the enum type
def is_prefixed_with_enum_type(identifier, enum_type):
    return identifier.startswith(enum_type.upper() + "_")

# Function to check if typedefs follow the naming convention with '_t' suffix
def is_typedef_correctly_named(name, typedef_base):
    return name == f"{typedef_base}_t"

# Define rules for each kind
def check_rule(finding):
    kind = finding['kind']
    name = finding['name']
    case = finding['case']
    
    # Rules mapping
    rules = {
        'Local Define': lambda: case == 'SNAKE_CASE' and finding['is_file_prefix'],
        'Local Struct': lambda: case == 'snake_case' and finding['is_file_prefix'],
        'Local Enum': lambda: case == 'snake_case' and finding['is_file_prefix'],
        'Local Enum Value': lambda: case == 'SNAKE_CASE' and finding['is_enum_prefix'],
        'Local Typedef': lambda: finding['is_typedef_base_and_suffix'],
        'Local Function': lambda: case == 'snake_case' and finding['is_file_prefix'],
        'Local Variable': lambda: case == 'snake_case' and finding['is_file_prefix'],
        
        'Global Define': lambda: case == 'SNAKE_CASE' and finding['is_file_prefix'],
        'Global Struct': lambda: case == 'snake_case' and finding['is_file_prefix'],
        'Global Enum': lambda: case == 'snake_case' and finding['is_file_prefix'],
        'Global Enum Value': lambda: case == 'SNAKE_CASE' and finding['is_enum_prefix'],
        'Global Typedef': lambda: finding['is_typedef_base_and_suffix'],
        'Global Function': lambda: case == 'snake_case' and finding['is_file_prefix'],
        'Global Variable': lambda: case == 'snake_case' and finding['is_file_prefix'],
        
        'Parameter': lambda: case == 'snake_case',
        'Member Variable': lambda: case == 'snake_case',
        'Auto Variable': lambda: case == 'snake_case',
    }

    # Check rule and return result
    return rules.get(kind, lambda: False)()

# Helper function to create a finding dictionary
def create_finding(node, kind, name=None, enum_type='', typedef_base=''):
    if name is None:
        name = node.spelling
    finding = {
        'name': name,
        'kind': kind,
        'enum_type': enum_type,
        'typedef_base': typedef_base,
        'is_file_prefix': is_prefixed_with_filename(name, c_file_name),
        'is_enum_prefix': is_prefixed_with_enum_type(name, enum_type),
        'is_typedef_base_and_suffix': is_typedef_correctly_named(name, typedef_base),
        'case': detect_case(name),
        'file': node.location.file.name,
        'line': node.location.line,
        'column': node.location.column,
    }
    finding['ok'] = "yes" if check_rule(finding) else "no"
    return finding

def visit_node(node, file_name, depth=0):
    file_extension = os.path.splitext(file_name)[1]

    if node.location.file and node.location.file.name == file_name:
        is_header = file_extension == '.h'

        if node.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
            kind = 'Global Define' if is_header else 'Local Define'
            findings.append(create_finding(node, kind))
        
        elif node.kind == clang.cindex.CursorKind.STRUCT_DECL:
            kind = 'Global Struct' if is_header else 'Local Struct'
            findings.append(create_finding(node, kind))
            for child in node.get_children():
                if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                    findings.append(create_finding(child, kind='Member Variable'))

        elif node.kind == clang.cindex.CursorKind.ENUM_DECL:
            kind = 'Global Enum' if is_header else 'Local Enum'
            findings.append(create_finding(node, kind))
            for child in node.get_children():
                if child.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL:
                    kind = 'Global Enum Value' if is_header else 'Local Enum Value'
                    findings.append(create_finding(child, kind, enum_type=node.spelling))

        elif node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            kind = 'Global Typedef' if is_header else 'Local Typedef'
            findings.append(create_finding(node, kind, typedef_base=node.underlying_typedef_type.spelling.split()[-1]))

        elif node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            if is_header or node.storage_class == clang.cindex.StorageClass.EXTERN:
                kind = 'Global Function'
            else:
                kind = 'Local Function'
            findings.append(create_finding(node, kind))
            for param in node.get_arguments():
                findings.append(create_finding(param, kind='Parameter'))

        elif node.kind == clang.cindex.CursorKind.VAR_DECL:
            if is_header or node.storage_class == clang.cindex.StorageClass.EXTERN:
                kind = 'Global Variable'
            else:
                kind = 'Local Variable' if node.storage_class == clang.cindex.StorageClass.STATIC else 'Auto Variable'
            findings.append(create_finding(node, kind))

    # Recurse through child nodes
    if node.kind != clang.cindex.CursorKind.TYPEDEF_DECL:
        for child in node.get_children():
            visit_node(child, file_name, depth + 1)

# Visit the root node (TranslationUnit) and traverse its children
visit_node(translation_unit.cursor, c_file_name)

# Print the findings in a nicely formatted table
print(tabulate(findings, headers="keys", tablefmt="simple"))
