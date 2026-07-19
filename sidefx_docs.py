"""Portable discovery and search for SideFX's bundled Houdini help.

No documentation is copied into this project.  The provider reads the
``hom.zip`` and ``nodes.zip`` archives shipped with the active Houdini
installation and emits portable references plus canonical SideFX web URLs.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from tool_registry import DocRef


_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def _version_key(value: str) -> tuple[int, int, int]:
    match = _VERSION_RE.search(value)
    if not match:
        return (0, 0, 0)
    return tuple(int(part or 0) for part in match.groups())


def _help_root_from_candidate(value: Optional[str | os.PathLike[str]]) -> Optional[Path]:
    if not value:
        return None
    path = Path(os.path.expandvars(os.path.expanduser(str(value))))
    candidates = (path, path / "help", path / "houdini" / "help")
    for candidate in candidates:
        if (candidate / "hom.zip").is_file() and (candidate / "nodes.zip").is_file():
            return candidate.resolve()
    return None


def _windows_install_roots() -> List[Path]:
    roots: List[Path] = []
    try:
        import winreg
    except ImportError:
        return roots
    key_paths = (
        r"SOFTWARE\Side Effects Software",
        r"SOFTWARE\WOW6432Node\Side Effects Software",
    )
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for key_path in key_paths:
            try:
                with winreg.OpenKey(hive, key_path) as root:
                    index = 0
                    while True:
                        try:
                            name = winreg.EnumKey(root, index)
                            index += 1
                        except OSError:
                            break
                        if not name.lower().startswith("houdini"):
                            continue
                        try:
                            with winreg.OpenKey(root, name) as child:
                                install_path, _ = winreg.QueryValueEx(child, "InstallPath")
                                roots.append(Path(install_path))
                        except OSError:
                            continue
            except OSError:
                continue
    return roots


def _mac_install_roots() -> List[Path]:
    roots: List[Path] = []
    applications = Path("/Applications/Houdini")
    if applications.is_dir():
        roots.extend(applications.glob("Houdini*.app/Contents/Frameworks/Houdini.framework/Versions/Current/Resources"))
    roots.extend(Path("/Applications").glob("Houdini*.app/Contents/Frameworks/Houdini.framework/Versions/Current/Resources"))
    return roots


def _hconfig_install_root() -> Optional[Path]:
    executable = shutil.which("hconfig")
    if not executable:
        return None
    try:
        completed = subprocess.run(
            [executable, "-ap"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    for line in completed.stdout.splitlines():
        match = re.match(r"\s*HFS\s*:?=\s*(.+?)\s*$", line)
        if match:
            return Path(match.group(1).strip('"'))
    return None


def _linux_install_roots() -> List[Path]:
    roots: List[Path] = []
    hconfig_root = _hconfig_install_root()
    if hconfig_root:
        roots.append(hconfig_root)
    for parent in (Path("/opt"), Path("/usr/local")):
        if parent.is_dir():
            roots.extend(parent.glob("hfs*"))
    return roots


def discover_help_root(
    environment: Optional[Mapping[str, str]] = None,
    houdini_info: Optional[Mapping[str, Any]] = None,
    system_name: Optional[str] = None,
    extra_install_roots: Sequence[str | os.PathLike[str]] = (),
) -> Optional[Path]:
    """Find the active Houdini help root without assuming a machine path."""

    env = environment if environment is not None else os.environ
    ordered: List[Optional[str | os.PathLike[str]]] = [env.get("HOUDINI_MCP_DOC_ROOT")]
    if houdini_info:
        ordered.extend((houdini_info.get("hfs"), houdini_info.get("hh")))
    ordered.extend((env.get("HFS"), env.get("HH")))
    ordered.extend(extra_install_roots)

    for value in ordered:
        found = _help_root_from_candidate(value)
        if found:
            return found

    system = (system_name or platform.system()).lower()
    if system == "windows":
        roots = _windows_install_roots()
    elif system == "darwin":
        roots = _mac_install_roots()
    else:
        roots = _linux_install_roots()
    roots.sort(key=lambda path: _version_key(str(path)), reverse=True)
    for root in roots:
        found = _help_root_from_candidate(root)
        if found:
            return found
    return None


def official_url(archive: str, entry: str) -> str:
    path = entry.replace("\\", "/")
    if path.endswith(".txt"):
        path = path[:-4] + ".html"
    if archive == "hom.zip":
        return f"https://www.sidefx.com/docs/houdini/hom/{path}"
    if archive == "nodes.zip":
        return f"https://www.sidefx.com/docs/houdini/nodes/{path}"
    return f"https://www.sidefx.com/docs/houdini/{path}"


def _clean_text(raw: str, fallback: str) -> tuple[str, str]:
    lines: List[str] = []
    for line in raw.replace("\r", "").split("\n"):
        value = line.strip()
        if not value or value.startswith(("#", "@", "=", "<?")):
            continue
        value = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", value)
        value = re.sub(r"[`*_{}|]", "", value)
        value = re.sub(r"\s+", " ", value).strip()
        if len(value) >= 3:
            lines.append(value)
        if len(lines) >= 3:
            break
    title = lines[0][:160] if lines else fallback
    summary = " ".join(lines[1:] or lines[:1])[:500]
    return title, summary


@dataclass(frozen=True)
class DocRecord:
    kind: str
    archive: str
    entry: str
    title: str
    summary: str
    web_url: str

    def as_dict(self, houdini_version: Optional[str]) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "kind": self.kind,
            "title": self.title,
            "summary": self.summary,
            "local_ref": f"{self.archive}:{self.entry}",
            "official_url": self.web_url,
        }
        if houdini_version:
            result["houdini_version"] = houdini_version
        return result


class SideFXDocsProvider:
    def __init__(
        self,
        help_root: Optional[Path] = None,
        houdini_version: Optional[str] = None,
        environment: Optional[Mapping[str, str]] = None,
        houdini_info: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.houdini_version = houdini_version or (
            str(houdini_info.get("version")) if houdini_info and houdini_info.get("version") else None
        )
        self.help_root = help_root or discover_help_root(environment, houdini_info)
        self._records: Optional[List[DocRecord]] = None

    @property
    def status(self) -> str:
        return "available" if self.help_root else "degraded"

    def _build_index(self) -> List[DocRecord]:
        if self._records is not None:
            return self._records
        records: List[DocRecord] = []
        if not self.help_root:
            self._records = records
            return records
        for archive_name, kind in (("hom.zip", "hom"), ("nodes.zip", "node")):
            archive_path = self.help_root / archive_name
            try:
                with zipfile.ZipFile(archive_path) as archive:
                    for entry in archive.namelist():
                        if not entry.endswith(".txt") or entry.startswith(("_", ".")):
                            continue
                        try:
                            raw = archive.read(entry)[:16384].decode("utf-8", errors="replace")
                        except (KeyError, OSError):
                            continue
                        fallback = Path(entry).stem
                        title, summary = _clean_text(raw, fallback)
                        records.append(
                            DocRecord(
                                kind=kind,
                                archive=archive_name,
                                entry=entry,
                                title=title,
                                summary=summary,
                                web_url=official_url(archive_name, entry),
                            )
                        )
            except (OSError, zipfile.BadZipFile):
                continue
        self._records = records
        return records

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        needle = query.strip().lower()
        if not needle or not self.help_root:
            return []
        ranked: List[tuple[int, str, DocRecord]] = []
        for record in self._build_index():
            entry = record.entry.lower()
            title = record.title.lower()
            summary = record.summary.lower()
            if needle not in f"{entry} {title} {summary}":
                continue
            stem = Path(entry).stem.lower()
            if stem == needle:
                score = 100
            elif stem.startswith(needle):
                score = 80
            elif needle in entry:
                score = 60
            elif needle in title:
                score = 40
            else:
                score = 20
            ranked.append((score, entry, record))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        capped = max(1, min(int(limit), 50))
        return [record.as_dict(self.houdini_version) for _, _, record in ranked[:capped]]

    def resolve_refs(self, refs: Iterable[DocRef]) -> List[Dict[str, Any]]:
        record_map = {(item.archive, item.entry): item for item in self._build_index()}
        results: List[Dict[str, Any]] = []
        for ref in refs:
            result = ref.as_dict(self.houdini_version)
            record = record_map.get((ref.archive, ref.entry))
            if record:
                result.update({"title": record.title, "summary": record.summary})
            result["available_locally"] = record is not None
            results.append(result)
        return results
