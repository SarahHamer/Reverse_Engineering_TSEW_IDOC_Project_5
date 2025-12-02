import os
import sys
import marshal
import dis
import types

# === CONFIG ===
# Folder that contains the raw members extracted from PYZ-00.pyz.
# Adjust this to match your actual path.
PYZ_ROOT = os.path.join("TheFactory.exe_extracted\PYZ-00.pyz_extracted", "PYZ-00.pyz")

# Output root directory for human-readable disassembly files
OUT_ROOT = "decompiled_to_py\PYZ-00.pyz_content"


def log(msg: str):
    print(msg)


def try_load_code_object(path: str):
    """
    Try to load a marshalled Python code object from a file.

    The files extracted from PYZ-00.pyz are usually raw marshalled
    code objects (no .pyc header), so we can feed them directly to
    marshal.loads().
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        log(f"[!] Could not read {path!r}: {e}")
        return None

    try:
        obj = marshal.loads(data)
    except Exception as e:
        # Not a marshalled object at all, or encrypted, or data.
        log(f"[skip] {path}: not a marshalled code object ({e})")
        return None

    if not isinstance(obj, types.CodeType):
        log(f"[skip] {path}: loaded object is {type(obj)}, not CodeType")
        return None

    return obj


def safe_name(name: str) -> str:
    """
    Make a filesystem-safe version of a qualified function name.
    """
    for ch in "<>:/\\ \t":
        name = name.replace(ch, "_")
    return name


def dump_code_object(code: types.CodeType, qualified_name: str, module_rel_path: str):
    """
    Write a readable disassembly of a single code object to a .dis.txt file.

    One file per function / code object to keep things small and focused.
    """
    # Derive a subdirectory from the module path, e.g.
    # module_rel_path = "pkg/mod" → base = "pkg/mod"
    base_without_ext = os.path.splitext(module_rel_path)[0]
    out_dir = os.path.join(OUT_ROOT, base_without_ext)
    os.makedirs(out_dir, exist_ok=True)

    out_file_name = safe_name(qualified_name) + ".dis.txt"
    out_path = os.path.join(out_dir, out_file_name)

    log(f"[+] Writing {out_path}")

    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"# Disassembly for {qualified_name}\n")
        out.write(f"# From module file: {module_rel_path}\n\n")

        out.write("## co_consts:\n")
        out.write(repr(code.co_consts))
        out.write("\n\n## co_names:\n")
        out.write(repr(code.co_names))
        out.write("\n\n## bytecode:\n\n")

        # Use dis.Bytecode for nicer, structured output
        bc = dis.Bytecode(code)
        for instr in bc:
            out.write(f"{instr.offset:4}: {instr.opname:20} {instr.argrepr}\n")


def walk_code_object(code: types.CodeType, qualified_name: str, module_rel_path: str):
    """
    Recursively walk a code object and all nested code objects (functions,
    methods, lambdas, comprehensions, etc.), dumping each one.
    """
    dump_code_object(code, qualified_name, module_rel_path)

    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            child_qual = f"{qualified_name}.{const.co_name}"
            walk_code_object(const, child_qual, module_rel_path)


def main():
    if not os.path.isdir(PYZ_ROOT):
        log(f"[-] PYZ_ROOT directory {PYZ_ROOT!r} not found.")
        sys.exit(1)

    os.makedirs(OUT_ROOT, exist_ok=True)

    for dirpath, dirnames, filenames in os.walk(PYZ_ROOT):
        for name in filenames:
            full_path = os.path.join(dirpath, name)
            # Module-relative path inside PYZ (for nicer folder layout)
            module_rel_path = os.path.relpath(full_path, PYZ_ROOT)

            log(f"[*] Processing {module_rel_path}")

            code = try_load_code_object(full_path)
            if code is None:
                continue

            # Derive a module-ish name: "pkg/sub/file" -> "pkg.sub.file"
            mod_name = os.path.splitext(module_rel_path)[0].replace(os.sep, ".")
            # Top-level code object qualified name starts as module name
            walk_code_object(code, mod_name, module_rel_path)

    log(f"[+] Done. Disassembly written under {OUT_ROOT!r}")


if __name__ == "__main__":
    main()