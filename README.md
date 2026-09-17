# JoaKApple

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
- Para a etapa de descriptografar, o programa **GnuPG** instalado no seu
  computador:
  - Windows: instale o [Gpg4win](https://gpg4win.org) (só isso, não precisa mexer em mais nada).
  - Linux: normalmente já vem instalado; se não vier, instale o pacote `gnupg` da sua distribuição.

## Como baixar e abrir o programa

Baixe a versão do seu sistema na página de releases:
**https://github.com/joasource/apple/releases**

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

- **"gpg não foi encontrado no PATH"**: falta instalar o Gpg4win (Windows)
  ou o `gnupg` (Linux) — veja "O que você precisa antes de começar".
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
enviada ao repositório. Os arquivos `baixar.py`, `conferir.py` e
`decriptar.py` na raiz são os scripts originais, mantidos só como
referência histórica.
