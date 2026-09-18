<p align="center">
  <img src="packaging/linux/icon.png" width="96" height="96" alt="Ícone do JoaKApple">
</p>

<h1 align="center">JoaKApple</h1>

<p align="center">
  <a href="https://github.com/joasource/JoaKApple/actions/workflows/ci.yml"><img src="https://github.com/joasource/JoaKApple/actions/workflows/ci.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/joasource/JoaKApple/actions/workflows/release.yml"><img src="https://github.com/joasource/JoaKApple/actions/workflows/release.yml/badge.svg" alt="Build Release"></a>
  <a href="https://github.com/joasource/JoaKApple/releases/latest"><img src="https://img.shields.io/github/v/release/joasource/JoaKApple" alt="Última release"></a>
  <img src="https://img.shields.io/badge/plataformas-Windows%20%7C%20Linux-0F6B62" alt="Plataformas suportadas">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licença-GPL--3.0-0F6B62" alt="Licença GPL-3.0"></a>
</p>

Programa para processar o retorno que a Apple manda em resposta a um
ofício judicial: ele **baixa** os arquivos, **confere** se cada um baixou
certinho (hash SHA256) e **descriptografa** os arquivos `.gpg` usando a
senha que a Apple forneceu.

Você pode rodar as três etapas juntas ou escolher só as que precisa (por
exemplo, só conferir arquivos que já foram baixados antes).

Autor: Joaquim Ferreira Silva Neto — joaquimfsneto@gmail.com

<p align="center">
  <img src="docs/screenshot.png" alt="Janela principal do JoaKApple: seleção do CSV da Apple e da pasta de destino, senha GPG, as três etapas do pipeline (Baixar/Verificar/Descriptografar) e a lista de arquivos com log ao lado." width="760">
</p>

## O que você precisa antes de começar

- O **arquivo CSV** que a Apple te mandou (a lista com os links dos arquivos).
- A **senha** que a Apple forneceu, se você for descriptografar os arquivos `.gpg`.
- Para a etapa de descriptografar, o programa precisa do **GnuPG**:
  - **Windows**: já vem embutido no `JoaKApple.exe` — não precisa instalar nada.
  - **Linux**: usa o `gnupg` do sistema, que normalmente já vem instalado; se
    não vier, instale o pacote `gnupg` da sua distribuição.

## Como baixar e abrir o programa

Baixe a versão do seu sistema na página de releases:
**https://github.com/joasource/JoaKApple/releases**
(o que mudou em cada versão está no [CHANGELOG](CHANGELOG.md))

- **Windows**: baixe `JoaKApple.exe` e dê dois cliques para abrir.
  - O Windows pode mostrar um aviso azul ("O Windows protegeu o computador").
    Isso acontece porque o programa não tem certificado pago da Microsoft,
    não porque tem algo de errado. Clique em **Mais informações** e depois em
    **Executar assim mesmo**.
- **Linux**: baixe `JoaKApple-x86_64.AppImage`, dê permissão de execução e rode:
  ```bash
  chmod +x JoaKApple-x86_64.AppImage
  ./JoaKApple-x86_64.AppImage
  ```
  Se aparecer erro relacionado a FUSE, rode assim:
  ```bash
  ./JoaKApple-x86_64.AppImage --appimage-extract-and-run
  ```

## Como usar

1. Abra o programa.
2. Em **Arquivo CSV da Apple**, clique em Selecionar e escolha o CSV que a Apple te enviou.
3. Em **Pasta de destino**, escolha onde os arquivos vão ser salvos.
4. Se for descriptografar, preencha a **Senha GPG** com a senha que a Apple forneceu.
5. Em **Etapas do pipeline**, marque o que você quer que rode:
   - **Baixar** — baixa os arquivos do CSV.
   - **Verificar** — confere se o hash de cada arquivo bate com o informado pela Apple.
   - **Descriptografar** — usa a senha para abrir os arquivos `.gpg`.

   Pode marcar as três, só uma, ou duas — o botão mostra a combinação escolhida.
6. Clique em **Iniciar** e acompanhe a lista de arquivos e o log na tela.

Ao final, na pasta de destino você vai encontrar:
- Os arquivos baixados (como a Apple mandou, ainda `.gpg` se estiverem criptografados).
- Uma subpasta `decriptado/` com os arquivos já descriptografados.
- Um arquivo `joakapple_log.txt` com o histórico de cada etapa (data e hora).

Rodar o programa de novo em cima da mesma pasta é seguro: arquivos que já
foram baixados, já conferidos ou já descriptografados são identificados e
pulados automaticamente — nada é refeito à toa.

## Modo texto (`--no-gui`, só no Linux)

No Linux, dá pra rodar tudo isso sem abrir janela nenhuma, direto do
terminal — útil pra servidor, script ou automação:

```bash
./JoaKApple-x86_64.AppImage --no-gui run --csv retorno.csv --output-dir ./saida
./JoaKApple-x86_64.AppImage --no-gui list --csv retorno.csv
./JoaKApple-x86_64.AppImage --no-gui delete --csv retorno.csv --output-dir ./saida --only arquivo.txt.gpg
./JoaKApple-x86_64.AppImage --no-gui report --responsavel "Fulano" --format docx --out termo.docx
```

Se faltar alguma informação obrigatória (ex.: `--csv`), ou se você passar
`--menu`/`-i`, um menu interativo simples pergunta o que falta — mesma
lógica da GUI, sem depender de nenhuma biblioteca nova.

A senha do GPG nunca vai numa flag em texto puro (ficaria visível em
`ps aux`/histórico do shell). Use uma destas opções:
- Prompt interativo (padrão, se o terminal permitir).
- `--passphrase-env NOME_DA_VARIAVEL` — lê de uma variável de ambiente já setada.
- `--passphrase-stdin` — lê uma linha do stdin: `echo "senha" | ... --passphrase-stdin`.

Rode `./JoaKApple-x86_64.AppImage --no-gui --help` (ou `run --help`,
`report --help` etc.) pra ver todas as opções de cada subcomando. O `.exe`
do Windows não tem esse modo — só a GUI.

## Se der algum problema

- **"gpg não foi encontrado no PATH"**: no Windows isso não deveria acontecer
  (o GnuPG vem embutido); no Linux, instale o pacote `gnupg` da sua
  distribuição.
- **"Hash inválido"** num arquivo: ele baixou incompleto ou corrompido.
  Apague o arquivo da pasta de destino e rode o programa de novo só com
  "Baixar" e "Verificar" marcados.
- **Senha incorreta**: o programa avisa qual arquivo falhou ao descriptografar;
  confira a senha exatamente como a Apple enviou (maiúsculas/minúsculas importam).

---

### Para quem for mexer no código

O código-fonte fica em `apple_toolkit/` (`core.py` é o motor do pipeline,
`gui.py` é a interface gráfica, `cli.py` é o modo texto Linux-only e
`app.py` é o ponto de entrada único que escolhe entre os dois conforme a
flag `--no-gui`). Os executáveis são gerados automaticamente pelo GitHub
Actions (`.github/workflows/release.yml`) a cada tag `vX.Y.Z` enviada ao
repositório — o `.exe` do Windows compila a partir de `gui.py` direto (sem
CLI); o AppImage do Linux compila a partir de `app.py`. Os arquivos em
`legacy/` (`baixar.py`, `conferir.py` e `decriptar.py`) são os scripts
originais, mantidos só como referência histórica.

Os testes automatizados (`apple_toolkit/tests/`) cobrem o motor do
pipeline: leitura de CSV, download, verificação de hash e descriptografia
(com um `gpg` real, se disponível no PATH). Rodam a cada push/PR via
`.github/workflows/ci.yml`. Pra rodar localmente:
```bash
pip install -r apple_toolkit/requirements-dev.txt
pytest apple_toolkit/tests -v
```

O ícone do app fica em `packaging/`, gerado por `packaging/make_icon.py`
(requer `pip install Pillow`): `linux/icon.png` é reaproveitado no
AppImage, na janela em tempo de execução (`gui.py`) e neste README;
`windows/icon.ico` é a versão multi-resolução usada no `.exe`;
`icon-1024.png` é uma cópia em alta resolução pra material de divulgação.
Pra mudar o design (cor, monograma), edite `make_icon.py` e rode
`python packaging/make_icon.py` de novo — ele regenera os três arquivos.

---

## Licença

Este projeto é distribuído sob a [GNU General Public License v3.0](LICENSE)
(GPL-3.0). Em resumo: você pode usar, estudar, modificar e redistribuir o
código livremente — inclusive comercialmente —, mas qualquer redistribuição
(modificada ou não) precisa continuar sob a mesma licença, manter os
créditos e avisos de copyright, e disponibilizar o código-fonte
correspondente. Não é permitido incorporar este código em software
proprietário/fechado.

Copyright (C) 2026 Joaquim Ferreira Silva Neto &lt;joaquimfsneto@gmail.com&gt;
