# Execução do projeto

## Requisitos

- Python 3.11 ou superior;
- acesso à internet para baixar os dados da ANP;
- PowerShell no fluxo recomendado para Windows;
- Docker Desktop somente se a camada PostgreSQL for utilizada;
- Power BI Desktop somente para construção ou atualização do dashboard.

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

## Executar com PostgreSQL

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -WithPostgres
```

O Docker Compose inicia o PostgreSQL e o projeto carrega os dois modelos dimensionais.

Para usar PostgreSQL e snapshot na mesma execução:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -WithPostgres -Snapshot
```

## Execução manual

Criar o ambiente:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
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
