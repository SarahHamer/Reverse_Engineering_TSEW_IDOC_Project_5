import os, sys
from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

EXE = "TheFactory.exe"
OUT_DIR = "TheFactory.exe_extracted\PYZ-00.pyz_extracted"

def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def extract_archive(archive_name: str, archive, base_out: str):
    # Recursively extract contents of PyInstaller archive
    print(f"[+] Processing archive {archive_name!r} ({type(archive).__name__})")

    # CArchiveReader: EXE / PKG container
    if isinstance(archive, CArchiveReader):
        for name, (pos, length, ulen, is_compressed, typecode) in archive.toc.items():
            # typecode 'z' = embedded PYZ/PKG
            if typecode == "z":
                try:
                    embedded = archive.open_embedded_archive(name)
                except Exception as e:
                    print(f"    [!] Could not open embedded archive {name!r}: {e}")
                    continue
                subdir = os.path.join(base_out, name.replace(os.sep, "_"))
                os.makedirs(subdir, exist_ok=True)
                extract_archive(name, embedded, subdir)
            else:
                # Normal member: extract raw bytes if possible
                try:
                    data = archive.extract(name)
                except Exception as e:
                    print(f"    [!] Failed to extract {name!r} from {archive_name!r}: {e}")
                    continue

                if data is None:
                    continue

                out_path = os.path.join(base_out, name)
                ensure_dir(out_path)
                with open(out_path, "wb") as f:
                    f.write(data)
                print(f"    [*] Wrote {out_path}")

    # ZlibArchiveReader: PYZ archive (pure Python bytecode / data)
    elif isinstance(archive, ZlibArchiveReader):
        for name, (typecode, pos, length) in archive.toc.items():
            try:
                # raw=True => get compressed member’s actual bytes
                data = archive.extract(name, raw=True)
            except Exception as e:
                print(f"    [!] Failed to extract {name!r} from {archive_name!r}: {e}")
                continue

            if data is None:
                continue

            out_path = os.path.join(base_out, name)
            ensure_dir(out_path)
            with open(out_path, "wb") as f:
                f.write(data)
            print(f"    [*] Wrote {out_path}")
    else:
        print(f"[!] Unknown archive type: {type(archive)}")


def main():
    if not os.path.isfile(EXE):
        print(f"[-] EXE {EXE!r} not found in current directory.")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)

    # Top-level EXE is a CArchiveReader
    top = CArchiveReader(EXE)
    extract_archive(EXE, top, OUT_DIR)
    print(f"[+] Done. All extracted to: {OUT_DIR!r}")


if __name__ == "__main__":
    main()