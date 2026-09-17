<p align="center">
  <img src="packaging/linux/icon.png" width="96" height="96" alt="Ícone do JoaKApple">
</p>

<h1 align="center">JoaKApple</h1>

<p align="center">
  <a href="https://github.com/joasource/apple/actions/workflows/ci.yml"><img src="https://github.com/joasource/apple/actions/workflows/ci.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/joasource/apple/actions/workflows/release.yml"><img src="https://github.com/joasource/apple/actions/workflows/release.yml/badge.svg" alt="Build Release"></a>
  <a href="https://github.com/joasource/apple/releases/latest"><img src="https://img.shields.io/github/v/release/joasource/apple" alt="Última release"></a>
  <img src="https://img.shields.io/badge/plataformas-Windows%20%7C%20Linux-0F6B62" alt="Plataformas suportadas">
</p>

Programa para processar o retorno que a Apple manda em resposta a um
ofício judicial: ele **baixa** os arquivos, **confere** se cada um baixou
certinho (hash SHA256) e **descriptografa** os arquivos `.gpg` usando a
senha que a Apple forneceu.

Você pode rodar as três etapas juntas ou escolher só as que precisa (por
exemplo, só conferir arquivos que já foram baixados antes).

Autor: Joaquim Ferreira Silva Neto — joaquimfsneto@gmail.com

## O que você precisa antes de começar

- O **arquivo CSV** que a Apple te mandou (a lista com os links dos arquivos).
- A **senha** que a Apple forneceu, se você for descriptografar os arquivos `.gpg`.
- Para a etapa de descriptografar, o programa precisa do **GnuPG**:
  - **Windows**: já vem embutido no `JoaKApple.exe` — não precisa instalar nada.
  - **Linux**: usa o `gnupg` do sistema, que normalmente já vem instalado; se
    não vier, instale o pacote `gnupg` da sua distribuição.

## Como baixar e abrir o programa

Baixe a versão do seu sistema na página de releases:
**https://github.com/joasource/apple/releases**
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
`gui.py` é a interface gráfica). Os executáveis são gerados automaticamente
pelo GitHub Actions (`.github/workflows/release.yml`) a cada tag `vX.Y.Z`
enviada ao repositório. Os arquivos em `legacy/` (`baixar.py`, `conferir.py`
e `decriptar.py`) são os scripts originais, mantidos só como referência
histórica.

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
