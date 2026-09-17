# Changelog

Histórico de versões do JoaKApple. Formato baseado no
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); as versões
seguem [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Adicionado
- Ícone próprio do app (paleta da GUI: verde-azulado + creme), embutido no
  `.exe` do Windows, no AppImage do Linux e carregado também na janela em
  tempo de execução.
- Badges de build/testes/release no README.
- Suíte de testes automatizados para o motor do pipeline (`core.py`) e
  workflow de CI rodando a cada push/PR.

## [1.2.1] - 2026-09-17

### Corrigido
- Versão exibida na tela ficava presa em "1.1.0" mesmo depois da tag
  v1.2.0, porque `APP_VERSION` é uma constante que precisa ser atualizada
  manualmente a cada release.
- Canto do painel de log com raio de borda diferente do resto do card
  (parecia um círculo flutuando solto no rodapé).

### Alterado
- Crédito do autor movido do rodapé para o cabeçalho da janela.

## [1.2.0] - 2026-09-17

### Adicionado
- GnuPG portátil embutido no build do Windows — não é mais necessário
  instalar nada à parte para descriptografar.

### Alterado
- GUI reconstruída do zero com CustomTkinter para bater com o mockup
  aprovado (a primeira versão em Tkinter/ttk puro foi rejeitada por não
  bater visualmente com o design aprovado).

### Corrigido
- Instalador do Gpg4win travando indefinidamente no CI do Windows —
  resolvido extraindo o instalador diretamente com 7-Zip em vez de
  executá-lo.

## [1.1.0] - 2026-09-17

### Adicionado
- Pipeline dividido em três etapas independentes (Baixar / Verificar /
  Descriptografar), que podem ser ativadas sozinhas ou em qualquer
  combinação — por exemplo, só conferir arquivos já baixados antes.

### Alterado
- README reescrito para o usuário final, não mais para quem só mexe no
  código.

## [1.0.0] - 2026-09-17

Primeira versão do toolkit unificado, substituindo os três scripts
originais (`baixar.py`, `conferir.py`, `decriptar.py`).

### Adicionado
- Motor de pipeline único (`apple_toolkit/core.py`) com download
  retomável, verificação de hash SHA256 e descriptografia GPG, com senha
  passada via stdin (nunca como argumento de linha de comando).
- Interface gráfica (`apple_toolkit/gui.py`).
- Build automatizado via GitHub Actions: executável Windows (PyInstaller)
  e AppImage Linux, publicados juntos numa release por tag `vX.Y.Z`.
- Crédito do autor nas notas de release do GitHub.
- Rebrand do projeto para **JoaKApple**.
