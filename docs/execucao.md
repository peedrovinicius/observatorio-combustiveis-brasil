# Execução do projeto

## Requisitos

- Python 3.11 ou superior;
- acesso à internet para baixar os dados da ANP;
- PowerShell no fluxo recomendado para Windows;
- Docker Desktop somente se a camada PostgreSQL for utilizada;
- Power BI Desktop somente para construção ou atualização do dashboard.

## Perfis de dependência

O projeto separa as dependências por finalidade:

- `requirements.txt`: execução do pipeline e PostgreSQL;
- `requirements-dev.txt`: runtime + pytest para testes e desenvolvimento;
- `requirements-notebook.txt`: runtime + Jupyter para análise exploratória.

O runner local e o CI usam `requirements-dev.txt`, evitando instalar Jupyter apenas para executar testes.

## Fluxo recomendado no Windows

Na raiz do repositório:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

O script:

1. cria `.venv` quando necessário;
2. instala as dependências;
3. executa os testes;
4. baixa as fontes oficiais;
5. processa os dados;
6. valida os dados antes da modelagem;
7. constrói os modelos dimensionais;
8. gera as tabelas analíticas;
9. produz relatório e gráficos locais.

## Gerar snapshot revisável

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -Snapshot
```

Além do pipeline, o comando gera ou atualiza:

```text
docs/resultados-2026.md
docs/index.html
docs/assets/
assets/snapshot/
README.md
```

O README recebe localmente a seção de resultados reais. O script não executa comandos Git de escrita.

Cada comando externo é verificado pelo código de saída. Falhas em criação do ambiente, instalação, testes, pipeline, Docker, carga PostgreSQL ou snapshot interrompem imediatamente o fluxo.

A atualização isolada do README também valida a existência e o conteúdo dos cinco PNGs do snapshot e do relatório de resultados. Assim, o bloco visual não é publicado com links quebrados ou arquivos vazios.

## Executar com PostgreSQL

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -WithPostgres
```

O Docker Compose inicia o PostgreSQL e o projeto carrega os dois modelos dimensionais.

O fluxo com PostgreSQL aguarda o `healthcheck` do serviço ficar saudável, com timeout de 60 segundos, antes de iniciar a carga. Uma inicialização incompleta interrompe o script em vez de tentar conectar prematuramente.

Para usar PostgreSQL e snapshot na mesma execução:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -WithPostgres -Snapshot
```

## Execução manual

Criar o ambiente:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Executar testes, incluindo a integração offline:

```powershell
python -m pytest
```

Executar o pipeline:

```powershell
python -m src.pipeline
```

Gerar snapshot:

```powershell
python -m src.snapshot
```

O snapshot recusa artefatos visuais mais antigos que os CSVs analíticos ou relatórios de qualidade atuais. Se houver reprocessamento desses insumos, execute `python -m src.reporting` antes do snapshot.

Não use `python -m src.site` nem `python -m src.publish_readme` para publicação isolada. Esses pontos de entrada são bloqueados para preservar a regra de publicação tudo ou nada.

Subir PostgreSQL:

```powershell
docker compose up -d postgres
python -m src.load_postgres
```

## Etapas do pipeline

```text
1. download da série agregada
2. download dos dados abertos por posto
3. inspeção dos arquivos brutos agregados
4. transformação da série agregada
5. consolidação da série agregada 2026
6. validação de qualidade agregada
7. construção do modelo estrela agregado
8. preparação da camada por posto
9. validação de qualidade por posto
10. construção do modelo estrela por posto
11. geração das tabelas analíticas agregadas
12. geração das análises por posto
13. geração do relatório e dos gráficos
```

## Arquivos não versionados

Por padrão, o Git ignora:

- dados brutos baixados;
- dados processados;
- relatórios de qualidade gerados;
- gráficos temporários em `assets/generated/`;
- arquivos binários temporários do Power BI;
- ambiente virtual;
- variáveis locais em `.env`.

O snapshot revisado em `assets/snapshot/`, `docs/resultados-2026.md` e `docs/index.html` pode ser versionado após conferência.


## Barreira de qualidade por posto

A modelagem por estabelecimento é executada somente depois da validação final da base consolidada.

A ordem é:

```text
ingestão e deduplicação
-> auditoria de ingestão
-> base consolidada por posto
-> quality_postos_2026.json
-> modelo estrela por posto
```

Se a validação detectar data inválida, data fora de 2026, preço inválido, preço não positivo, campo obrigatório ausente ou duplicidade na chave de negócio, o pipeline encerra antes de gerar `model_postos/`.

Os módulos `src.build_station_model` e `src.station_analytics` repetem a validação antes de produzir modelo ou métricas, mesmo quando executados manualmente.


## Barreira de qualidade agregada

A série consolidada de 2026 também é protegida quando os módulos são executados fora do pipeline.

A ordem segura é:

```text
consolidação agregada
-> auditoria de ingestão
-> quality_2026.json
-> modelo estrela agregado
-> analytics agregados
```

Os módulos `src.build_model` e `src.analytics` recalculam a qualidade da série consolidada antes de gerar dimensões, fato ou KPIs.

Se houver inconsistência bloqueante, a execução manual encerra antes de escrever novas saídas.

Uma base vazia com schema correto também é reprovada. A ausência de linhas não é tratada como uma validação bem-sucedida.


## Publicação transacional de CSVs derivados

Os diretórios de modelo e analytics são atualizados por lote:

```text
data/processed/model/
data/processed/model_postos/
data/processed/analytics/
data/processed/analytics_postos/
```

Cada lote é primeiro gravado em staging. Depois, os CSVs anteriores do diretório são movidos para backup temporário e somente então as novas saídas são instaladas.

Se uma escrita no staging ou a instalação de qualquer arquivo falhar, o snapshot anterior do diretório permanece disponível ou é restaurado integralmente.

Arquivos não CSV presentes nesses diretórios não são removidos pela rotina.


## Publicação transacional do relatório visual

A etapa final do pipeline trata os cinco PNGs gerados e `reports/insights_2026.md` como um único bundle lógico.

Todos os arquivos são produzidos em staging e validados antes da substituição. Uma falha durante a geração não altera o bundle anterior. Uma falha durante a instalação aciona rollback dos gráficos e do relatório de insights.


## Publicação transacional do snapshot versionável

Quando `python -m src.snapshot` é executado, o projeto monta primeiro um snapshot completo em staging.

O bundle inclui:

```text
assets/snapshot/
docs/resultados-2026.md
docs/assets/
docs/index.html
README.md
```

O `README.md` é copiado para staging e recebe o bloco de resultados somente nessa cópia. O site também é construído a partir do snapshot em staging.

A substituição dos cinco alvos só começa quando todo o conjunto foi gerado. Os alvos anteriores são mantidos em backup temporário durante a troca. Se qualquer instalação falhar, os itens novos já instalados são removidos e o snapshot versionável anterior é restaurado integralmente.

Arquivos de documentação que não fazem parte desse bundle, como `docs/site.css`, metodologia e documentação técnica, não são substituídos pela rotina.


## Consolidação e auditoria como bundle

A consolidação agregada publica `data/processed/precos_semanais_2026.csv` e `reports/aggregate_ingestion_audit_2026.json` como um único par lógico.

A camada por posto aplica a mesma regra a `data/processed/precos_postos_2026.csv` e `reports/station_ingestion_audit_2026.json`.

O CSV e o JSON são preparados em staging. A troca só acontece depois que ambos existem e possuem conteúdo. Se a instalação do segundo arquivo falhar, o primeiro arquivo novo é removido e o par anterior é restaurado.


## Cadeia de frescor das saídas

A publicação visual valida a ordem temporal dos artefatos antes de gerar ou versionar resultados. A cadeia de frescor validada é:

```text
base processada
-> relatório de qualidade aprovado
-> analytics
-> reporting
-> snapshot público
```

Se uma etapa anterior for regenerada depois de uma etapa posterior, a publicação é bloqueada e informa qual módulo precisa ser reexecutado.


## Downloaders ativos

Os pontos de entrada de aquisição suportados são:

```powershell
python -m src.download_history
python -m src.download_open_data
```

`src.download_anp` é mantido apenas por compatibilidade com testes antigos de descoberta e seu `main()` é bloqueado. Ele não deve ser usado para gravar dados raw.


## Proveniência entre raw e processed

A transformação da série histórica publica:

```text
data/processed/history_transform_manifest.json
```

Esse manifesto liga os CSVs processados ao `data/raw/history_manifest.json` por SHA-256. A consolidação verifica o hash do manifesto raw atual, o tamanho e SHA-256 de cada CSV processado e a correspondência exata do conjunto de arquivos.

Por isso, não edite manualmente os CSVs históricos em `data/processed/`. Se qualquer arquivo ou manifesto divergir, reexecute:

```powershell
python -m src.transform
python -m src.consolidate
```

A transformação publica os CSVs e o manifesto processado como um único bundle com rollback.
