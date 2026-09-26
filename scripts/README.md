# Scripts locais

## run_local.ps1

Fluxo recomendado para Windows.

Execução padrão:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

Executa:

1. criação do ambiente virtual, quando necessário;
2. instalação das dependências;
3. testes;
4. pipeline completo da ANP;
5. geração dos relatórios e gráficos locais.

### Com PostgreSQL

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -WithPostgres
```

Também inicia o PostgreSQL via Docker Compose e carrega os dois modelos dimensionais.

### Com snapshot versionável

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -Snapshot
```

Também cria:

```text
docs/resultados-2026.md
assets/snapshot/
```

O snapshot também atualiza localmente a seção de resultados do `README.md`, apontando para os gráficos reais gerados.

O script não executa `git add`, `git commit` ou `git push`. Revise o relatório, os gráficos e o diff do README antes de versionar.
