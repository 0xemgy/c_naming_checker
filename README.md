# c_naming_checker

## TODO
- test extracting with pragmas and attributes, maybe further special cases, and other files than main.c
- add naming detection (with file prefix, camelCase/PascalCase/snake_case/SNAKE_CASE, enum values with enum type prefix yes/no, and typedefs == typedef_base + _t)
- add argparse, add debug logging, add error output
- add json config file (i.e. File Prefix only for global stuff, FilePrefix_globalFunction or FilePrefixGlobalFunction etc.)