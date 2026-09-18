"""
JoaKApple - ponto de entrada unico: GUI por padrao, CLI de texto com
--no-gui (so no build Linux — o .exe do Windows continua apontando pra
gui.py direto, ver .github/workflows/release.yml).

Autor: Joaquim Ferreira Silva Neto <joaquimfsneto@gmail.com>
"""

import sys


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--no-gui":
        import cli

        return cli.main(sys.argv[2:])
    import gui

    gui.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
