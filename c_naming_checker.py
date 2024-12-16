import argparse
import clang.cindex
import os
import re
import sys

# List to hold findings
findings = []

error = False

# Rules mapping
rules = {
    'Local Define':     {   'case' : 'SNAKE_CASE'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Local Struct':     {   'case' : 'snake_case'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Local Enum':       {   'case' : 'snake_case'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Local Enum Value': {   'case' : 'SNAKE_CASE'   , 'is_file_prefix' : True   , 'is_enum_prefix' : True   , 'is_typedef_base_and_suffix' : False  },
    'Local Typedef':    {   'case' : 'snake_case'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : True   },
    'Local Function':   {   'case' : 'snake_case'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Local Variable':   {   'case' : 'snake_case'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Global Define':    {   'case' : 'SNAKE_CASE'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Global Struct':    {   'case' : 'snake_case'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Global Enum':      {   'case' : 'snake_case'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Global Enum Value':{   'case' : 'SNAKE_CASE'   , 'is_file_prefix' : True   , 'is_enum_prefix' : True   , 'is_typedef_base_and_suffix' : False  },
    'Global Typedef':   {   'case' : 'snake_case'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : True   },
    'Global Function':  {   'case' : 'snake_case'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Global Variable':  {   'case' : 'snake_case'   , 'is_file_prefix' : True   , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Parameter':        {   'case' : 'snake_case'   , 'is_file_prefix' : False  , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Member Variable':  {   'case' : 'snake_case'   , 'is_file_prefix' : False  , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
    'Auto Variable':    {   'case' : 'snake_case'   , 'is_file_prefix' : False  , 'is_enum_prefix' : False  , 'is_typedef_base_and_suffix' : False  },
}


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
    return identifier.startswith(base_name.lower() + "_") or identifier.startswith(base_name.upper() + "_") or identifier == base_name.lower() or identifier == base_name.upper()

# Function to check if the identifier is prefixed with the enum type
def is_prefixed_with_enum_type(identifier, enum_type):
    return identifier.startswith(enum_type.upper() + "_")

# Function to check if typedefs follow the naming convention with '_t' suffix
def is_typedef_correctly_named(name, typedef_base):
    return name == f"{typedef_base}_t"

def check_rule(finding):
    for key, value in rules[finding['kind']].items():
        if value and finding.get(key) != value:
            return False
    return True

def generate_error_message(finding):
    file = finding['file']
    line = finding['line']
    column = finding['column']
    kind = finding['kind']
    name = finding['name']
    typedef_base = finding['typedef_base']
    enum_type = finding['enum_type']

    rule = rules[kind]
    case = rule['case']

    msg = f"{file}:{line}:{column}: error: '{name}' ('{kind}') should be"

    n = 0
    if rule['case'] != finding['case']:
        msg += f" in {case}"
        n+=1

    if rule['is_file_prefix'] and not finding['is_file_prefix']:
        if n > 0:
            msg += ","
        n += 1
        msg += f" prefixed with file name "
        filename = os.path.splitext(os.path.basename(file))[0]

        if case == "SNAKE_CASE":
            filename = filename.upper()

        msg += f"'{filename}_'"

    if rule['is_enum_prefix'] and not finding['is_enum_prefix']:
        if n > 0:
            msg += ","
        n += 1
        msg += f" prefixed with enum name '{enum_type.upper()}_'"
    if rule['is_typedef_base_and_suffix'] and not finding['is_typedef_base_and_suffix']:
        if n > 0:
            msg += ","
        n += 1
        msg += f" prefixed with typedef base name '{typedef_base}' and suffixed with '_t'"

    return msg

# Helper function to create a finding dictionary
def create_finding(file_name, node, kind, name=None, enum_type='', typedef_base=''):
    if name is None:
        name = node.spelling
    finding = {
        'name': name,
        'kind': kind,
        'enum_type': enum_type,
        'typedef_base': typedef_base,
        'is_file_prefix': is_prefixed_with_filename(name, file_name),
        'is_enum_prefix': is_prefixed_with_enum_type(name, enum_type),
        'is_typedef_base_and_suffix': is_typedef_correctly_named(name, typedef_base),
        'case': detect_case(name),
        'file': node.location.file.name,
        'line': node.location.line,
        'column': node.location.column,
    }
    finding['ok'] = check_rule(finding)
    return finding

def visit_node(node, file_name, depth=0):
    file_extension = os.path.splitext(file_name)[1]

    if node.location.file and node.location.file.name == file_name:
        is_header = file_extension == '.h'

        if node.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
            kind = 'Global Define' if is_header else 'Local Define'
            findings.append(create_finding(file_name, node, kind))
        
        elif node.kind == clang.cindex.CursorKind.STRUCT_DECL:
            kind = 'Global Struct' if is_header else 'Local Struct'
            findings.append(create_finding(file_name, node, kind))
            for child in node.get_children():
                if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                    findings.append(create_finding(file_name, child, kind='Member Variable'))

        elif node.kind == clang.cindex.CursorKind.ENUM_DECL:
            kind = 'Global Enum' if is_header else 'Local Enum'
            findings.append(create_finding(file_name, node, kind))
            for child in node.get_children():
                if child.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL:
                    kind = 'Global Enum Value' if is_header else 'Local Enum Value'
                    findings.append(create_finding(file_name, child, kind, enum_type=node.spelling))

        elif node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            kind = 'Global Typedef' if is_header else 'Local Typedef'
            findings.append(create_finding(file_name, node, kind, typedef_base=node.underlying_typedef_type.spelling.split()[-1]))

        elif node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            if is_header or node.storage_class == clang.cindex.StorageClass.EXTERN:
                kind = 'Global Function'
            else:
                kind = 'Local Function'
            findings.append(create_finding(file_name, node, kind))
            for param in node.get_arguments():
                findings.append(create_finding(file_name, param, kind='Parameter'))

        elif node.kind == clang.cindex.CursorKind.VAR_DECL:
            if is_header or node.storage_class == clang.cindex.StorageClass.EXTERN:
                kind = 'Global Variable'
            else:
                kind = 'Local Variable' if node.storage_class == clang.cindex.StorageClass.STATIC else 'Auto Variable'
            findings.append(create_finding(file_name, node, kind))

    # Recurse through child nodes
    if node.kind != clang.cindex.CursorKind.TYPEDEF_DECL:
        for child in node.get_children():
            visit_node(child, file_name, depth + 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check C identifiers for naming convention compliance.")
    parser.add_argument("--files", nargs="+", required=True, help="List of source and header files.")
    parser.add_argument("--libclang", required=True, help="Path to libclang.dll.")
    args = parser.parse_args()

    # Set the path to the Clang library for Windows (libclang.dll)
    clang.cindex.Config.set_library_file(args.libclang)

    # Initialize the Clang index
    index = clang.cindex.Index.create()

    # Parse the C file
    for file in args.files:
        if os.path.isfile(file):
            translation_unit = index.parse(file, options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
            visit_node(translation_unit.cursor, file)
        else:
            error = True
            print(f"{file}:1:1: error: File not found")


    for finding in findings:
        if not finding['ok']:
            error = True
            print(generate_error_message(finding))

    sys.exit(error)
