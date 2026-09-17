"""
JoaKApple - motor do pipeline (baixar, conferir hash, decriptar).

Autor: Joaquim Ferreira Silva Neto <joaquimfsneto@gmail.com>

Este modulo nao depende de interface grafica: pode ser usado tanto pela GUI
(gui.py) quanto por um script de linha de comando, se necessario.
"""

from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CONNECT_TIMEOUT = 15
READ_TIMEOUT = 60
MAX_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = 5
CHUNK_SIZE = 1024 * 1024  # 1 MiB
GPG_TIMEOUT_SECONDS = 300

# Nomes de coluna aceitos no CSV da Apple (variam entre exportacoes/idiomas)
COLUMN_ALIASES = {
    "file_name": ["File_Name", "File Name", "FileName", "Filename", "Nome_Arquivo"],
    "file_link": ["File_Link", "File Link", "FileLink", "Link", "URL", "Download_Link"],
    "sha256": ["GPG_SHA256", "SHA256", "Sha256", "Hash", "GPG_Sha256"],
}


class PipelineError(Exception):
    """Erro fatal que impede o pipeline de iniciar (config invalida, gpg ausente etc.)."""


def check_gpg_available() -> bool:
    return shutil.which("gpg") is not None


def _resolve_column(fieldnames: list[str], aliases: list[str]) -> Optional[str]:
    normalized = {f.strip().lower(): f for f in fieldnames if f}
    for alias in aliases:
        hit = normalized.get(alias.strip().lower())
        if hit:
            return hit
    return None


@dataclass
class FileEntry:
    file_name: str
    file_link: str
    sha256_expected: Optional[str]
    status: str = "pendente"
    message: str = ""

    @property
    def is_encrypted(self) -> bool:
        return self.file_name.lower().endswith(".gpg")


@dataclass
class PipelineSummary:
    total: int = 0
    concluidos: int = 0
    ja_existiam: int = 0
    hash_invalido: int = 0
    erros: int = 0
    cancelados: int = 0
    elapsed_seconds: float = 0.0


@dataclass
class PipelineConfig:
    csv_path: Path
    output_dir: Path
    passphrase: str = ""
    max_workers: int = 4
    download: bool = True
    verify: bool = True
    decrypt: bool = True
    log_path: Optional[Path] = None

    def __post_init__(self):
        self.csv_path = Path(self.csv_path)
        self.output_dir = Path(self.output_dir)
        if self.log_path is None:
            self.log_path = self.output_dir / "joakapple_log.txt"
        else:
            self.log_path = Path(self.log_path)

    @property
    def decrypted_dir(self) -> Path:
        return self.output_dir / "decriptado"


def load_entries(csv_path: Path) -> list[FileEntry]:
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise PipelineError(f"Arquivo CSV nao encontrado: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise PipelineError("CSV vazio ou sem cabecalho.")

        col_name = _resolve_column(reader.fieldnames, COLUMN_ALIASES["file_name"])
        col_link = _resolve_column(reader.fieldnames, COLUMN_ALIASES["file_link"])
        col_hash = _resolve_column(reader.fieldnames, COLUMN_ALIASES["sha256"])

        if not col_name or not col_link:
            raise PipelineError(
                "Nao foi possivel identificar as colunas de nome/link do arquivo no CSV. "
                f"Cabecalho encontrado: {reader.fieldnames}"
            )

        entries: list[FileEntry] = []
        for row in reader:
            file_name = (row.get(col_name) or "").strip()
            file_link = (row.get(col_link) or "").strip()
            sha256_expected = (row.get(col_hash) or "").strip().lower() if col_hash else ""

            if not file_name or not file_link:
                continue

            entries.append(
                FileEntry(
                    file_name=file_name,
                    file_link=file_link,
                    sha256_expected=sha256_expected or None,
                )
            )

    if not entries:
        raise PipelineError("Nenhuma linha valida encontrada no CSV.")

    return entries


def _sha256_of_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            data = fh.read(CHUNK_SIZE)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=MAX_ATTEMPTS,
        backoff_factor=RETRY_BACKOFF_SECONDS,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _download(
    session: requests.Session,
    entry: FileEntry,
    dest: Path,
    cancel_event: threading.Event,
    log: Callable[[str], None],
) -> bool:
    """Baixa entry.file_link para dest, com retomada em arquivo .part e retries."""
    part_path = dest.with_suffix(dest.suffix + ".part")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        if cancel_event.is_set():
            return False
        try:
            with session.get(
                entry.file_link, stream=True, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            ) as response:
                response.raise_for_status()
                with part_path.open("wb") as fh:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if cancel_event.is_set():
                            fh.close()
                            part_path.unlink(missing_ok=True)
                            return False
                        if chunk:
                            fh.write(chunk)
            part_path.replace(dest)
            return True
        except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha de rede
            log(f"[{entry.file_name}] tentativa {attempt}/{MAX_ATTEMPTS} falhou: {exc}")
            part_path.unlink(missing_ok=True)
            if attempt < MAX_ATTEMPTS:
                for _ in range(RETRY_BACKOFF_SECONDS * attempt):
                    if cancel_event.is_set():
                        return False
                    time.sleep(1)
            else:
                entry.message = f"Falha no download apos {MAX_ATTEMPTS} tentativas: {exc}"
                return False
    return False


def _decrypt(
    entry: FileEntry,
    encrypted_path: Path,
    decrypted_path: Path,
    passphrase: str,
    log: Callable[[str], None],
) -> bool:
    decrypted_path.parent.mkdir(parents=True, exist_ok=True)
    comando = [
        "gpg",
        "--batch",
        "--yes",
        "--pinentry-mode",
        "loopback",
        "--passphrase-fd",
        "0",
        "--output",
        str(decrypted_path),
        "--decrypt",
        str(encrypted_path),
    ]
    try:
        result = subprocess.run(
            comando,
            input=passphrase.encode("utf-8"),
            capture_output=True,
            timeout=GPG_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            entry.message = f"gpg falhou: {stderr or 'erro desconhecido'}"
            decrypted_path.unlink(missing_ok=True)
            return False
        return True
    except subprocess.TimeoutExpired:
        entry.message = "gpg excedeu o tempo limite"
        decrypted_path.unlink(missing_ok=True)
        return False
    except Exception as exc:  # noqa: BLE001
        entry.message = f"erro ao executar gpg: {exc}"
        decrypted_path.unlink(missing_ok=True)
        return False


def process_entry(
    entry: FileEntry,
    config: PipelineConfig,
    session: requests.Session,
    cancel_event: threading.Event,
    log: Callable[[str], None],
    on_update: Callable[[FileEntry], None],
) -> None:
    dest = config.output_dir / entry.file_name
    decrypted_path = config.decrypted_dir / Path(entry.file_name).stem

    if config.decrypt and entry.is_encrypted and decrypted_path.exists():
        entry.status = "concluido"
        entry.message = "ja existia descriptografado"
        on_update(entry)
        return

    if cancel_event.is_set():
        entry.status = "cancelado"
        on_update(entry)
        return

    # --- download (etapa opcional, com retomada: pula se ja existe) ---
    if config.download:
        if dest.exists():
            entry.message = "arquivo ja baixado"
        else:
            entry.status = "baixando"
            on_update(entry)
            log(f"Iniciando download de {entry.file_name}")
            ok = _download(session, entry, dest, cancel_event, log)
            if cancel_event.is_set():
                entry.status = "cancelado"
                on_update(entry)
                return
            if not ok:
                entry.status = "erro"
                on_update(entry)
                log(f"[{entry.file_name}] ERRO: {entry.message}")
                return
            log(f"Download de {entry.file_name} concluido")
    elif not dest.exists():
        entry.status = "erro"
        entry.message = "arquivo nao encontrado (etapa de download desmarcada)"
        on_update(entry)
        log(f"[{entry.file_name}] ERRO: {entry.message}")
        return

    # --- verificacao de hash (etapa opcional) ---
    if config.verify:
        if entry.sha256_expected:
            entry.status = "conferindo"
            on_update(entry)
            hash_calculado = _sha256_of_file(dest)
            if hash_calculado.lower() != entry.sha256_expected.lower():
                entry.status = "hash_invalido"
                entry.message = (
                    f"hash esperado {entry.sha256_expected} != calculado {hash_calculado}"
                )
                on_update(entry)
                log(f"[{entry.file_name}] HASH DIVERGENTE: {entry.message}")
                return
            log(f"Hash de {entry.file_name} confere")
        else:
            log(f"[{entry.file_name}] sem hash no CSV, verificacao pulada")
    else:
        log(f"[{entry.file_name}] verificacao de hash desmarcada, etapa pulada")

    # --- descriptografia (etapa opcional) ---
    if config.decrypt and entry.is_encrypted:
        entry.status = "decriptando"
        on_update(entry)
        ok = _decrypt(entry, dest, decrypted_path, config.passphrase, log)
        if not ok:
            entry.status = "erro"
            on_update(entry)
            log(f"[{entry.file_name}] ERRO na descriptografia: {entry.message}")
            return
        log(f"{entry.file_name} descriptografado em {decrypted_path}")

    entry.status = "concluido"
    entry.message = entry.message or "ok"
    on_update(entry)


def run_pipeline(
    config: PipelineConfig,
    entries: list[FileEntry],
    on_update: Callable[[FileEntry], None],
    log: Callable[[str], None],
    cancel_event: Optional[threading.Event] = None,
) -> PipelineSummary:
    if cancel_event is None:
        cancel_event = threading.Event()

    if entries and any(e.is_encrypted for e in entries) and config.decrypt:
        if not check_gpg_available():
            raise PipelineError(
                "O executavel 'gpg' nao foi encontrado no PATH. "
                "Instale o Gpg4win (https://gpg4win.org) para descriptografar os arquivos."
            )
        if not config.passphrase:
            raise PipelineError("Senha (passphrase) do GPG nao informada.")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    if config.decrypt:
        config.decrypted_dir.mkdir(parents=True, exist_ok=True)

    log_lock = threading.Lock()

    def safe_log(message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        with log_lock:
            with config.log_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        log(line)

    start = time.monotonic()
    session = _make_session()

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=max(1, config.max_workers)) as executor:
        futures = [
            executor.submit(process_entry, entry, config, session, cancel_event, safe_log, on_update)
            for entry in entries
        ]
        for future in futures:
            future.result()  # propaga excecoes inesperadas em vez de engoli-las

    elapsed = time.monotonic() - start

    summary = PipelineSummary(total=len(entries), elapsed_seconds=elapsed)
    for entry in entries:
        if entry.status == "concluido":
            if "ja existia" in entry.message:
                summary.ja_existiam += 1
            summary.concluidos += 1
        elif entry.status == "hash_invalido":
            summary.hash_invalido += 1
        elif entry.status == "cancelado":
            summary.cancelados += 1
        elif entry.status == "erro":
            summary.erros += 1

    safe_log(
        "Pipeline finalizado: "
        f"{summary.concluidos}/{summary.total} concluidos, "
        f"{summary.hash_invalido} com hash invalido, "
        f"{summary.erros} com erro, "
        f"{summary.cancelados} cancelados, "
        f"em {summary.elapsed_seconds:.1f}s"
    )

    return summary
