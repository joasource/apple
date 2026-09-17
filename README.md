# Apple Toolkit — Oficio Judicial

Ferramenta para processar o retorno da Apple a um oficio judicial: baixa os
arquivos listados no CSV disponibilizado, confere o hash SHA256 de cada um e,
por fim, descriptografa os arquivos `.gpg` com a senha fornecida pela Apple.

Autor: Joaquim Ferreira Silva Neto — joaquimfsneto@gmail.com

## Estrutura

- `apple_toolkit/core.py` — motor do pipeline (download com retomada e
  retries, verificacao de hash, descriptografia via GPG, log com timestamp).
- `apple_toolkit/gui.py` — interface grafica (Tkinter, sem dependencias
  externas alem do `requests`).
- `baixar.py`, `conferir.py`, `decriptar.py` — scripts originais, mantidos
  apenas como referencia histórica; o `apple_toolkit` os substitui.

## Uso (GUI)

Pre-requisitos: Python 3.10+ e, para a etapa de descriptografia, o
[Gpg4win](https://gpg4win.org) instalado (o `gpg.exe` precisa estar no PATH).

```bash
pip install -r apple_toolkit/requirements.txt
python apple_toolkit/gui.py
```

Na janela, informe o CSV da Apple, a pasta de destino e a senha do GPG, ajuste
o numero de downloads simultaneos se quiser, e clique em **Iniciar**. Os
arquivos baixados ficam na pasta escolhida; os descriptografados vao para a
subpasta `decriptado/` (o arquivo `.gpg` original e preservado). Um log com
data/hora de cada etapa e gravado em `apple_toolkit_log.txt` dentro da pasta
de destino.

O pipeline e seguro para reexecutar: arquivos ja baixados, ja conferidos ou ja
descriptografados sao detectados e pulados automaticamente.

## Executaveis para Windows e Linux (release automatica)

O repositorio tem um workflow do GitHub Actions
(`.github/workflows/release.yml`) que compila, em paralelo:

- `AppleToolkit.exe` — em `windows-latest`, com PyInstaller (`--onefile`).
- `AppleToolkit-x86_64.AppImage` — em `ubuntu-latest`, com PyInstaller
  (`--onedir`) empacotado em um AppImage via `appimagetool`
  (assets de empacotamento em `packaging/linux/`).

Os dois artefatos sao publicados juntos em uma unica release do GitHub.

Para gerar uma nova release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Isso dispara o workflow, que compila os dois executaveis e os anexa a uma
nova release com o mesmo nome da tag. Tambem e possivel disparar
manualmente pela aba **Actions → Build Release → Run workflow** no GitHub,
informando a versao desejada.

Nenhum dos dois executaveis inclui o GnuPG — quem for usar a
descriptografia precisa ter o `gpg` instalado separadamente:
[Gpg4win](https://gpg4win.org) no Windows, ou o pacote `gnupg` da
distribuicao no Linux (geralmente ja vem instalado).

No Linux, o AppImage e um arquivo unico: basta dar permissao de execucao
(`chmod +x AppleToolkit-x86_64.AppImage`) e rodar. Em distribuicoes sem FUSE
instalado, execute com `./AppleToolkit-x86_64.AppImage --appimage-extract-and-run`.
