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

Também cria ou atualiza:

```text
docs/resultados-2026.md
docs/index.html
docs/assets/
assets/snapshot/
README.md
```

O `README.md` recebe uma seção visual com os gráficos reais e `docs/index.html` vira um relatório web estático baseado nos mesmos dados processados.

O script não executa `git add`, `git commit` ou `git push`. Revise os resultados e o diff antes de versionar.
