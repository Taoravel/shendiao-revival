"""Read MDMP stream/exception/thread evidence without loading a native image.

This intentionally small offline reader rejects out-of-range file references.
It reports x86 register contexts and conservative stack candidates, never an
asserted symbolic backtrace. No process, debugger, registry or network is used.

Methods: diagnosing-bugs compares exception/time/context evidence before cause
hypotheses; codebase-design hides MDMP layout behind a file-in/summary interface.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct


STREAM_NAMES = {
    3: "ThreadList", 4: "ModuleList", 5: "MemoryList", 6: "Exception",
    7: "SystemInfo", 8: "ThreadExList", 9: "Memory64List", 10: "CommentA",
    11: "CommentW", 12: "HandleData", 15: "MiscInfo", 16: "MemoryInfoList",
    17: "ThreadInfoList", 18: "HandleOperationList", 19: "Token", 24: "ThreadNames",
}


class DumpError(ValueError):
    pass


def utc(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


class Minidump:
    def __init__(self, filename):
        self.path = Path(filename).resolve()
        self.data = self.path.read_bytes()
        if len(self.data) < 32 or self.data[:4] != b"MDMP":
            raise DumpError("Expected an MDMP header")
        _, self.version, count, directory, self.checksum, self.timestamp, self.flags = self.unpack("<6IQ", 0)
        if count > 4096:
            raise DumpError("Unreasonable stream count")
        self.streams = []
        self.by_type = {}
        for index in range(count):
            kind, size, rva = self.unpack("<III", directory + index * 12)
            self.take(rva, size)
            record = {"type": kind, "name": STREAM_NAMES.get(kind, "Unknown"), "size": size, "rva": rva}
            self.streams.append(record)
            self.by_type.setdefault(kind, []).append(record)
        self.modules = self._modules()
        self.memory = []
        self.threads = self._threads()
        self._memory_lists()

    def take(self, offset, size):
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise DumpError(f"Out-of-range MDMP reference: offset={offset}, size={size}")
        return self.data[offset:offset + size]

    def unpack(self, form, offset):
        return struct.unpack(form, self.take(offset, struct.calcsize(form)))

    def string(self, rva):
        size = self.unpack("<I", rva)[0]
        if size & 1:
            raise DumpError("Odd UTF-16 string byte length")
        return self.take(rva + 4, size).decode("utf-16-le", errors="replace")

    def _stream(self, kind):
        records = self.by_type.get(kind, [])
        if len(records) > 1:
            raise DumpError(f"Duplicate standard stream {kind}")
        return records[0] if records else None

    def _modules(self):
        stream = self._stream(4)
        if stream is None:
            return []
        base = stream["rva"]
        count = self.unpack("<I", base)[0]
        if 4 + count * 108 > stream["size"]:
            raise DumpError("Truncated module list")
        result = []
        for index in range(count):
            offset = base + 4 + index * 108
            address, size, checksum, timestamp, name = self.unpack("<QIIII", offset)
            version = self.unpack("<13I", offset + 24)
            result.append({"name": self.string(name), "base": address, "size": size,
                           "timestamp_utc": utc(timestamp), "checksum": checksum,
                           "file_version": [version[2] >> 16, version[2] & 65535,
                                            version[3] >> 16, version[3] & 65535]})
        return result

    def symbol(self, address):
        for module in self.modules:
            if module["base"] <= address < module["base"] + module["size"]:
                name = module["name"].replace("\\", "/").rsplit("/", 1)[-1]
                return f"{name}+0x{address - module['base']:x}"
        return None

    def context(self, size, rva):
        raw = self.take(rva, size)
        if len(raw) >= 204:
            flags = self.unpack("<I", rva)[0]
            if flags & 0x10000:
                registers = {name: self.unpack("<I", rva + offset)[0] for name, offset in (
                    ("edi", 156), ("esi", 160), ("ebx", 164), ("edx", 168),
                    ("ecx", 172), ("eax", 176), ("ebp", 180), ("eip", 184),
                    ("eflags", 192), ("esp", 196))}
                return {"architecture": "x86", "flags": flags, "size": size,
                        "registers": registers, "instruction": self.symbol(registers["eip"]),
                        "register_groups_present": [name for bit, name in (
                            (1, "control"), (2, "integer"), (4, "segments"),
                            (8, "floating_point"), (16, "debug"), (32, "extended")) if flags & bit],
                        "limitation": "Only register groups present in ContextFlags are guaranteed valid; integer registers may be incidental in a control-only exception context."}
        return {"architecture": "unparsed", "size": size, "rva": rva}

    def _threads(self):
        stream = self._stream(3)
        if stream is None:
            return []
        base = stream["rva"]
        count = self.unpack("<I", base)[0]
        if 4 + count * 48 > stream["size"]:
            raise DumpError("Truncated thread list")
        result = []
        for index in range(count):
            offset = base + 4 + index * 48
            tid, suspended, priority_class, priority, teb, stack, size, rva, context_size, context_rva = self.unpack("<IIIIQQIIII", offset)
            self.take(rva, size)
            self.memory.append((stack, size, rva))
            result.append({"id": tid, "suspend_count": suspended, "priority_class": priority_class,
                           "priority": priority, "teb": teb,
                           "stack": {"address": stack, "size": size, "rva": rva},
                           "context": self.context(context_size, context_rva)})
        return result

    def _memory_lists(self):
        stream = self._stream(5)
        if stream:
            base = stream["rva"]
            count = self.unpack("<I", base)[0]
            if 4 + count * 16 > stream["size"]:
                raise DumpError("Truncated memory list")
            for index in range(count):
                start, size, rva = self.unpack("<QII", base + 4 + index * 16)
                self.take(rva, size)
                self.memory.append((start, size, rva))
        stream = self._stream(9)
        if stream:
            base = stream["rva"]
            count, data_rva = self.unpack("<QQ", base)
            if 16 + count * 16 > stream["size"]:
                raise DumpError("Truncated memory64 list")
            for index in range(count):
                start, size = self.unpack("<QQ", base + 16 + index * 16)
                self.take(data_rva, size)
                self.memory.append((start, size, data_rva))
                data_rva += size

    def read_memory(self, address, size):
        for start, count, rva in self.memory:
            if start <= address and address + size <= start + count:
                return self.take(rva + address - start, size)
        return None

    def exception(self):
        stream = self._stream(6)
        if stream is None:
            return None
        base = stream["rva"]
        if stream["size"] < 168:
            raise DumpError("Truncated exception stream")
        thread, _, code, flags, record, address, count, _ = self.unpack("<IIIIQQII", base)
        if count > 15:
            raise DumpError("Invalid exception parameter count")
        parameters = self.unpack("<15Q", base + 40)[:count]
        size, rva = self.unpack("<II", base + 160)
        return {"thread_id": thread, "code": f"0x{code:08x}", "flags": flags,
                "record": record, "address": address, "module_offset": self.symbol(address),
                "parameters": list(parameters), "context": self.context(size, rva)}

    def stack_evidence(self, thread, limit=24):
        context = thread["context"]
        if context["architecture"] != "x86":
            return {"frame_chain": [], "stack_candidates": []}
        registers = context["registers"]
        frames, seen = [], set()
        pointer = registers["ebp"]
        for _ in range(limit):
            if pointer in seen or pointer & 3:
                break
            seen.add(pointer)
            frame = self.read_memory(pointer, 8)
            if frame is None:
                break
            following, return_address = struct.unpack("<II", frame)
            frames.append({"frame": pointer, "return_address": return_address,
                           "module_offset": self.symbol(return_address)})
            if following <= pointer:
                break
            pointer = following
        candidates = []
        stack = thread["stack"]
        raw = self.read_memory(stack["address"], stack["size"]) or b""
        for offset in range(0, len(raw) - 3, 4):
            value = struct.unpack_from("<I", raw, offset)[0]
            symbol = self.symbol(value)
            if symbol:
                candidates.append({"stack_address": stack["address"] + offset,
                                   "value": value, "module_offset": symbol})
                if len(candidates) >= limit:
                    break
        return {"frame_chain": frames, "stack_candidates": candidates,
                "limitation": "Frame-pointer links and module-range matches are clues, not a symbolized crash backtrace."}

    def summary(self):
        system = self._stream(7)
        system_info = None
        if system and system["size"] >= 32:
            offset = system["rva"]
            arch, level, revision, cpus, product, major, minor, build, platform, csd = self.unpack("<HHHBBIIIII", offset)
            system_info = {"architecture": arch, "processor_level": level, "processor_revision": revision,
                           "processor_count": cpus, "product_type": product, "os_version": [major, minor, build],
                           "platform_id": platform, "service_pack": self.string(csd) if csd else ""}
        stat = self.path.stat()
        threads = [{**thread, **self.stack_evidence(thread)} for thread in self.threads]
        exception = self.exception()
        exception_stack = None
        if exception and exception["context"]["architecture"] == "x86":
            thread = next((item for item in self.threads if item["id"] == exception["thread_id"]), None)
            if thread:
                start = exception["context"]["registers"]["esp"]
                end = thread["stack"]["address"] + thread["stack"]["size"]
                if thread["stack"]["address"] <= start < end:
                    at_exception = {**thread, "context": exception["context"],
                                    "stack": {**thread["stack"], "address": start, "size": end - start}}
                    exception_stack = {"start": start, "size": end - start,
                                       **self.stack_evidence(at_exception, limit=96)}
        return {"path": str(self.path), "size": len(self.data),
                "sha256": hashlib.sha256(self.data).hexdigest(), "header_version": self.version,
                "header_timestamp_utc": utc(self.timestamp), "file_mtime_utc": utc(stat.st_mtime),
                "flags": self.flags, "streams": self.streams, "system": system_info,
                "exception": exception, "exception_stack": exception_stack,
                "threads": threads, "modules": self.modules,
                "memory_ranges": len(self.memory)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {"dumps": [Minidump(filename).summary() for filename in args.dump],
              "method": "offline bounded MDMP stream/context comparison; no native code execution"}
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
