"""
JoaKApple - motor do pipeline (baixar, conferir hash, decriptar).

Autor: Joaquim Ferreira Silva Neto <joaquimfsneto@gmail.com>

Este modulo nao depende de interface grafica: pode ser usado tanto pela GUI
(gui.py) quanto por um script de linha de comando, se necessario.

Copyright (C) 2026 Joaquim Ferreira Silva Neto <joaquimfsneto@gmail.com>

Este programa e' software livre: voce pode redistribui-lo e/ou modifica-lo
sob os termos da GNU General Public License, conforme publicada pela Free
Software Foundation, na versao 3 da licenca, ou (a seu criterio) qualquer
versao posterior. Este programa e' distribuido na esperanca de ser util,
mas SEM NENHUMA GARANTIA; nem mesmo a garantia implicita de COMERCIALIZACAO
ou ADEQUACAO A UM PROPOSITO ESPECIFICO. Veja a GNU General Public License
para mais detalhes: <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import csv
import hashlib
import os
import shutil
import subprocess
import sys
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
PROGRESS_THROTTLE_SECONDS = 0.2

# Nomes de coluna aceitos no CSV da Apple (variam entre exportacoes/idiomas)
COLUMN_ALIASES = {
    "file_name": ["File_Name", "File Name", "FileName", "Filename", "Nome_Arquivo"],
    "file_link": ["File_Link", "File Link", "FileLink", "Link", "URL", "Download_Link"],
    "sha256": ["GPG_SHA256", "SHA256", "Sha256", "Hash", "GPG_Sha256"],
}


class PipelineError(Exception):
    """Erro fatal que impede o pipeline de iniciar (config invalida, gpg ausente etc.)."""


# --------------------------------------------------------------- log estruturado

def _format_size(n: float) -> str:
    """Formatacao compacta de bytes para uso em campos de log (ex.: 8.54MB)."""
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)}{unit}" if unit == "B" else f"{size:.2f}{unit}"
        size /= 1024
    return f"{size:.2f}TB"


def _fmt_field(value) -> str:
    if isinstance(value, float):
        text = f"{value:.3f}"
    else:
        text = str(value)
    if not text or any(ch in text for ch in " \t\"="):
        text = text.replace('"', '\\"')
        return f'"{text}"'
    return text


def log_line(level: str, component: str, message: str, **fields) -> str:
    """Monta uma linha de log estruturada: timestamp, nivel, componente, mensagem
    e campos tecnicos chave=valor (bytes, duracao, velocidade, tentativa, etc.)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"{ts} [{level:<5}] {component:<10} {message}"
    if fields:
        line += "  " + " ".join(f"{k}={_fmt_field(v)}" for k, v in fields.items())
    return line


def _bundled_gpg_path() -> Optional[Path]:
    """Caminho do gpg embutido no executavel (PyInstaller), se houver.

    So o build do Windows embute um GnuPG portatil em ``gnupg-bin/`` ao lado
    do executavel; no Linux o GnuPG do sistema (quase sempre ja instalado)
    continua sendo usado via PATH.
    """
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return None
    name = "gpg.exe" if os.name == "nt" else "gpg"
    candidate = Path(base) / "gnupg-bin" / name
    return candidate if candidate.is_file() else None


def _gpg_executable() -> str:
    bundled = _bundled_gpg_path()
    return str(bundled) if bundled else "gpg"


def check_gpg_available() -> bool:
    return _bundled_gpg_path() is not None or shutil.which("gpg") is not None


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
    # Preenchidos quando a etapa de verificacao do pipeline calcula o hash do
    # arquivo, pra' quem vier depois (ex.: tela do Termo de Recebimento) poder
    # reaproveitar em vez de recalcular — ver cached_file_hash().
    sha256_computed: Optional[str] = None
    sha256_computed_stat: Optional[tuple[int, float]] = None

    @property
    def is_encrypted(self) -> bool:
        return self.file_name.lower().endswith(".gpg")


@dataclass
class ProgressEvent:
    """Progresso de bytes de uma etapa em andamento (download ou verificacao de hash),
    para a barra por arquivo na GUI/CLI."""

    file_name: str
    bytes_done: int
    bytes_total: int
    phase: str = "download"  # "download" | "hash"


def format_eta(seconds: float) -> str:
    """mm:ss (ou hh:mm:ss acima de 1h) para exibir tempo restante estimado."""
    if seconds != seconds or seconds < 0:  # nan ou negativo
        seconds = 0
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


@dataclass
class SpeedEstimate:
    speed_bps: float
    eta_seconds: Optional[float]


class ProgressTracker:
    """Velocidade media desde o inicio do progresso atual; reinicia quando
    bytes_done cai (nova tentativa recomecando do zero)."""

    def __init__(self):
        self._start: Optional[float] = None
        self._last_bytes = 0

    def update(self, bytes_done: int, bytes_total: int, now: Optional[float] = None) -> SpeedEstimate:
        if now is None:
            now = time.monotonic()
        if self._start is None or bytes_done < self._last_bytes:
            self._start = now  # primeiro evento, ou nova tentativa reiniciando do zero
        self._last_bytes = bytes_done
        elapsed = now - self._start
        speed = bytes_done / elapsed if elapsed > 0.2 and bytes_done > 0 else 0.0

        eta_seconds: Optional[float] = None
        if speed > 0 and bytes_total > bytes_done:
            eta_seconds = (bytes_total - bytes_done) / speed

        return SpeedEstimate(speed_bps=speed, eta_seconds=eta_seconds)


def aggregate_progress(
    events: dict[str, "ProgressEvent"], start_time: float, now: Optional[float] = None
) -> dict:
    """Agrega bytes/velocidade/ETA de varios ProgressEvent em andamento (lote inteiro)."""
    if now is None:
        now = time.monotonic()

    bytes_done = sum(e.bytes_done for e in events.values())
    bytes_known = sum(e.bytes_total for e in events.values() if e.bytes_total > 0)
    elapsed = max(now - start_time, 0.001)
    speed_bps = bytes_done / elapsed if bytes_done > 0 else 0.0

    eta_seconds: Optional[float] = None
    if speed_bps > 0 and bytes_known > bytes_done:
        eta_seconds = (bytes_known - bytes_done) / speed_bps

    return {
        "bytes_done": bytes_done,
        "bytes_known": bytes_known,
        "speed_bps": speed_bps,
        "eta_seconds": eta_seconds,
    }


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


def sha256_of_file(
    path: Path, on_progress: Optional[Callable[[int, int], None]] = None
) -> str:
    hasher = hashlib.sha256()
    total = path.stat().st_size
    bytes_done = 0
    last_emit = 0.0
    with path.open("rb") as fh:
        while True:
            data = fh.read(CHUNK_SIZE)
            if not data:
                break
            hasher.update(data)
            bytes_done += len(data)
            if on_progress:
                now = time.monotonic()
                if now - last_emit >= PROGRESS_THROTTLE_SECONDS:
                    on_progress(bytes_done, total)
                    last_emit = now
    if on_progress:
        on_progress(bytes_done, total)  # evento final, garante 100%
    return hasher.hexdigest()


def cached_file_hash(entry: FileEntry, path: Path) -> Optional[str]:
    """Hash ja calculado pro arquivo (na verificacao do pipeline), se o arquivo
    em disco nao mudou desde entao (mesmo tamanho/mtime); None se precisa
    (re)calcular."""
    if entry.sha256_computed is None or entry.sha256_computed_stat is None:
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    if (stat.st_size, stat.st_mtime) != entry.sha256_computed_stat:
        return None
    return entry.sha256_computed


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
    on_progress: Optional[Callable[[FileEntry, int, int, str], None]] = None,
) -> bool:
    """Baixa entry.file_link para dest, com retomada em arquivo .part e retries."""
    part_path = dest.with_suffix(dest.suffix + ".part")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        if cancel_event.is_set():
            return False
        started = time.monotonic()
        bytes_done = 0
        last_emit = 0.0
        try:
            with session.get(
                entry.file_link, stream=True, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            ) as response:
                response.raise_for_status()
                total_bytes = int(response.headers.get("Content-Length", 0) or 0)
                log(
                    log_line(
                        "INFO", "download", "conexao estabelecida",
                        file=entry.file_name, tentativa=f"{attempt}/{MAX_ATTEMPTS}",
                        status_http=response.status_code,
                        tamanho=_format_size(total_bytes) if total_bytes else "desconhecido",
                    )
                )
                if on_progress:
                    on_progress(entry, 0, total_bytes, "download")
                with part_path.open("wb") as fh:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if cancel_event.is_set():
                            fh.close()
                            part_path.unlink(missing_ok=True)
                            return False
                        if chunk:
                            fh.write(chunk)
                            bytes_done += len(chunk)
                            now = time.monotonic()
                            if on_progress and (now - last_emit) >= PROGRESS_THROTTLE_SECONDS:
                                on_progress(entry, bytes_done, total_bytes, "download")
                                last_emit = now
                if on_progress:
                    on_progress(entry, bytes_done, total_bytes or bytes_done, "download")
            part_path.replace(dest)
            duration = max(time.monotonic() - started, 0.001)
            log(
                log_line(
                    "OK", "download", "download concluido",
                    file=entry.file_name, bytes=bytes_done,
                    duracao=f"{duration:.2f}s", velocidade=f"{_format_size(bytes_done / duration)}/s",
                )
            )
            return True
        except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha de rede
            log(
                log_line(
                    "WARN", "download", "tentativa falhou",
                    file=entry.file_name, tentativa=f"{attempt}/{MAX_ATTEMPTS}",
                    bytes_recebidos=bytes_done, erro=str(exc),
                )
            )
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
        _gpg_executable(),
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
    started = time.monotonic()
    try:
        result = subprocess.run(
            comando,
            input=passphrase.encode("utf-8"),
            capture_output=True,
            timeout=GPG_TIMEOUT_SECONDS,
        )
        duration = time.monotonic() - started
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            entry.message = f"gpg falhou: {stderr or 'erro desconhecido'}"
            decrypted_path.unlink(missing_ok=True)
            log(
                log_line(
                    "ERROR", "gpg", "descriptografia falhou",
                    file=entry.file_name, exit_code=result.returncode,
                    duracao=f"{duration:.2f}s", stderr=stderr or "erro desconhecido",
                )
            )
            return False
        log(
            log_line(
                "OK", "gpg", "descriptografia concluida",
                file=entry.file_name, exit_code=0, duracao=f"{duration:.2f}s",
                saida=str(decrypted_path),
            )
        )
        return True
    except subprocess.TimeoutExpired:
        entry.message = "gpg excedeu o tempo limite"
        decrypted_path.unlink(missing_ok=True)
        log(
            log_line(
                "ERROR", "gpg", "tempo limite excedido",
                file=entry.file_name, timeout_s=GPG_TIMEOUT_SECONDS,
            )
        )
        return False
    except Exception as exc:  # noqa: BLE001
        entry.message = f"erro ao executar gpg: {exc}"
        decrypted_path.unlink(missing_ok=True)
        log(log_line("ERROR", "gpg", "erro ao executar processo", file=entry.file_name, erro=str(exc)))
        return False


def delete_entry_files(entry: FileEntry, output_dir: Path) -> list[Path]:
    """Remove do disco os arquivos ja obtidos para ``entry`` (baixado, .part e
    descriptografado), sem tocar no restante do lote. Retorna os caminhos removidos."""
    output_dir = Path(output_dir)
    dest = output_dir / entry.file_name
    part_path = dest.with_suffix(dest.suffix + ".part")
    decrypted_path = output_dir / "decriptado" / Path(entry.file_name).stem

    removed: list[Path] = []
    for path in (dest, part_path, decrypted_path):
        if path.is_file():
            path.unlink()
            removed.append(path)
    return removed


def process_entry(
    entry: FileEntry,
    config: PipelineConfig,
    session: requests.Session,
    cancel_event: threading.Event,
    log: Callable[[str], None],
    on_update: Callable[[FileEntry], None],
    on_progress: Optional[Callable[[FileEntry, int, int, str], None]] = None,
) -> None:
    dest = config.output_dir / entry.file_name
    decrypted_path = config.decrypted_dir / Path(entry.file_name).stem
    thread_name = threading.current_thread().name

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
            size = dest.stat().st_size
            if on_progress:
                on_progress(entry, size, size, "download")
            log(log_line("DEBUG", "download", "arquivo ja existe, pulando", file=entry.file_name, bytes=size))
        else:
            entry.status = "baixando"
            on_update(entry)
            log(log_line("INFO", "download", "iniciando download", file=entry.file_name, thread=thread_name, url=entry.file_link))
            ok = _download(session, entry, dest, cancel_event, log, on_progress=on_progress)
            if cancel_event.is_set():
                entry.status = "cancelado"
                on_update(entry)
                log(log_line("WARN", "download", "cancelado pelo usuario", file=entry.file_name))
                return
            if not ok:
                entry.status = "erro"
                on_update(entry)
                log(log_line("ERROR", "download", "falha definitiva", file=entry.file_name, motivo=entry.message))
                return
    elif not dest.exists():
        entry.status = "erro"
        entry.message = "arquivo nao encontrado (etapa de download desmarcada)"
        on_update(entry)
        log(log_line("ERROR", "download", "arquivo ausente", file=entry.file_name, motivo=entry.message))
        return

    # --- verificacao de hash (etapa opcional) ---
    if config.verify:
        if entry.sha256_expected:
            entry.status = "conferindo"
            on_update(entry)
            hash_started = time.monotonic()
            hash_progress = (
                (lambda done, total: on_progress(entry, done, total, "hash"))
                if on_progress
                else None
            )
            hash_calculado = sha256_of_file(dest, on_progress=hash_progress)
            hash_duration = time.monotonic() - hash_started
            dest_stat = dest.stat()
            entry.sha256_computed = hash_calculado
            entry.sha256_computed_stat = (dest_stat.st_size, dest_stat.st_mtime)
            if hash_calculado.lower() != entry.sha256_expected.lower():
                entry.status = "hash_invalido"
                entry.message = (
                    f"hash esperado {entry.sha256_expected} != calculado {hash_calculado}"
                )
                on_update(entry)
                log(
                    log_line(
                        "ERROR", "hash", "divergencia de integridade",
                        file=entry.file_name, esperado=entry.sha256_expected,
                        calculado=hash_calculado, duracao=f"{hash_duration:.2f}s",
                    )
                )
                return
            log(
                log_line(
                    "OK", "hash", "integridade confirmada",
                    file=entry.file_name, sha256=hash_calculado, duracao=f"{hash_duration:.2f}s",
                )
            )
        else:
            log(log_line("DEBUG", "hash", "sem hash no CSV, verificacao pulada", file=entry.file_name))
    else:
        log(log_line("DEBUG", "hash", "etapa desmarcada pelo usuario", file=entry.file_name))

    # --- descriptografia (etapa opcional) ---
    if config.decrypt and entry.is_encrypted:
        entry.status = "decriptando"
        on_update(entry)
        log(log_line("INFO", "gpg", "iniciando descriptografia", file=entry.file_name, thread=thread_name))
        ok = _decrypt(entry, dest, decrypted_path, config.passphrase, log)
        if not ok:
            entry.status = "erro"
            on_update(entry)
            return

    entry.status = "concluido"
    entry.message = entry.message or "ok"
    on_update(entry)
    log(log_line("OK", "pipeline", "arquivo finalizado", file=entry.file_name, status=entry.status))


def run_pipeline(
    config: PipelineConfig,
    entries: list[FileEntry],
    on_update: Callable[[FileEntry], None],
    log: Callable[[str], None],
    cancel_event: Optional[threading.Event] = None,
    on_progress: Optional[Callable[[FileEntry, int, int, str], None]] = None,
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
        with log_lock:
            with config.log_path.open("a", encoding="utf-8") as fh:
                fh.write(message + "\n")
        log(message)

    safe_log(
        log_line(
            "INFO", "pipeline", "iniciando lote",
            arquivos=len(entries), workers=max(1, config.max_workers),
            baixar=config.download, verificar=config.verify, decriptar=config.decrypt,
        )
    )

    start = time.monotonic()
    session = _make_session()

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(
        max_workers=max(1, config.max_workers), thread_name_prefix="worker"
    ) as executor:
        futures = [
            executor.submit(
                process_entry, entry, config, session, cancel_event, safe_log, on_update, on_progress
            )
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
        log_line(
            "INFO", "pipeline", "lote finalizado",
            concluidos=f"{summary.concluidos}/{summary.total}",
            ja_existiam=summary.ja_existiam, hash_invalido=summary.hash_invalido,
            erros=summary.erros, cancelados=summary.cancelados,
            duracao=f"{summary.elapsed_seconds:.1f}s",
        )
    )

    return summary
