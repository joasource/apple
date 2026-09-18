# Changelog

Histórico de versões do JoaKApple. Formato baseado no
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); as versões
seguem [SemVer](https://semver.org/lang/pt-BR/).

## [1.5.0] - 2026-09-18

### Adicionado
- Barra de progresso individual por arquivo na lista de downloads, mostrando
  percentual, bytes baixados/total e velocidade em tempo real (antes só
  existia a barra agregada do lote inteiro).
- Lista de arquivos agora tem barra de rolagem própria e uma checkbox por
  arquivo para selecionar quais processar antes de clicar em "Iniciar" —
  arquivos desmarcados são ignorados no lote.
- Botão "Excluir" em cada linha, para apagar do disco (com confirmação) o
  que já foi baixado/descriptografado daquele arquivo específico, sem sair
  do programa.
- Log reformulado com cara de log técnico profissional: timestamp com
  milissegundos, nível (`DEBUG`/`INFO`/`OK`/`WARN`/`ERROR`) colorido, nome
  do componente e campos chave=valor (bytes, duração, velocidade, tentativa,
  thread, exit code do gpg, hash calculado, etc.), em vez de frases soltas.

### Corrigido
- Geração do Termo de Recebimento podia preencher hashes/volume/quantidade
  com placeholders mesmo tendo arquivos já baixados em disco: o botão
  "Gerar termo" ficava clicável antes do cálculo de hash (assíncrono)
  terminar, e não recarregava a lista de arquivos se o pipeline não tivesse
  rodado nesta sessão. Agora o botão fica desabilitado ("Calculando
  hashes…") até o cálculo terminar, e a janela carrega o CSV sozinha
  quando necessário.
- Texto padrão do Termo de Recebimento dizia que os hashes eram dos
  arquivos "contidos nos pacotes compactados (formato ZIP)" — os arquivos
  que a Apple envia são criptografados em GPG, não compactados em ZIP.
  Corrigido para "pacotes criptografados (formato GPG)".

## [1.4.1] - 2026-09-17

### Corrigido
- Janela principal usava um tamanho fixo em pixels (`1040x820`) que não
  se adaptava a fontes/DPI diferentes, cortando o botão "Gerar Termo de
  Recebimento…" no rodapé até o usuário esticar a janela manualmente.
  A janela agora calcula o próprio tamanho a partir do conteúdo, então
  nada fica escondido independente da tela.

## [1.4.0] - 2026-09-17

### Adicionado
- Verificação no workflow de release: a tag `vX.Y.Z` só publica se
  `APP_VERSION` (em `gui.py`) e a primeira entrada deste CHANGELOG
  baterem com a versão da tag. Evita repetir o bug de versão exibida
  ficando desatualizada em relação à tag publicada.
- Botão "Gerar Termo de Recebimento…" na GUI, que abre uma janela para
  preencher os dados manuais do Termo de Recebimento e Identificação de
  Evidência Telemática (processo, PIC/inquérito, responsável, etc.) e
  gera o texto já com quantidade de arquivos, volume total e a tabela de
  hashes SHA-256 calculados automaticamente a partir dos arquivos
  recebidos na pasta de destino.
- Duas formas de exportar o termo gerado: botão "Copiar" (texto simples
  + HTML formatado na área de transferência, para colar com Arial 12 e
  espaçamento 1,5 direto no Word/LibreOffice) e botão "Salvar .docx"
  (gera um arquivo Word já pronto, com títulos, negrito, tabela nativa
  e a mesma formatação Arial 12/espaçamento 1,5).

## [1.3.0] - 2026-09-17

### Adicionado
- Ícone próprio do app (paleta da GUI: verde-azulado + creme), embutido no
  `.exe` do Windows, no AppImage do Linux e carregado também na janela em
  tempo de execução.
- Badges de build/testes/release no README.
- Suíte de testes automatizados para o motor do pipeline (`core.py`) e
  workflow de CI rodando a cada push/PR.
- Este CHANGELOG.

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
