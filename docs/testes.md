# Testes

O projeto usa `pytest` para validar regras unitárias e um fluxo de integração offline.

## Execução

```bash
python -m pytest
```

O runner local executa a mesma suíte antes do pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

## Cobertura lógica

A suíte verifica, entre outros pontos:

- descoberta das fontes oficiais;
- reconhecimento de CSV, ZIP e XLSX pelo conteúdo;
- substituição transacional de datasets por posto com staging e restauração;
- substituição transacional do lote histórico e do manifesto com rollback integral;
- normalização de schema;
- substituição transacional do lote de CSVs processados;
- preservação integral do lote processado anterior quando uma planilha é inválida ou a instalação falha;
- datas e decimais;
- consolidação de 2026;
- qualidade agregada;
- proveniência obrigatória da fato agregada;
- coerência semântica das estatísticas agregadas;
- identidade geográfica mínima por nível antes da modelagem;
- identidade e deduplicação de postos;
- suporte ao CNPJ alfanumérico sem remoção de letras;
- preservação de zeros à esquerda na leitura de CNPJ;
- bloqueio de CNPJ com formato estrutural incompatível e fallback de posto incompleto;
- exigência dos cinco componentes do fallback de identidade;
- preservação de linhas com fallback incompleto sem deduplicação indevida;
- exclusão de fallback incompleto da auditoria de sobreposição;
- precedência entre publicações sobrepostas;
- auditoria de exclusões agregadas e por posto;
- publicação transacional das bases consolidadas junto das respectivas auditorias;
- substituição transacional dos lotes de modelo e analytics;
- rollback integral dos CSVs derivados quando uma escrita ou instalação falha;
- modelo estrela agregado;
- barreira de qualidade antes da modelagem agregada;
- modelo estrela por posto;
- presença da proveniência `fonte_arquivo` antes da modelagem por posto;
- KPIs agregados;
- semântica produto + unidade de medida nos analytics agregados;
- relação etanol/gasolina somente entre observações da mesma unidade;
- bloqueio de grupos ambíguos na relação etanol/gasolina;
- barreira de qualidade antes dos analytics agregados;
- análises por estabelecimento;
- analytics por posto preservam séries independentes por combinação de produto e unidade de medida;
- barreira de qualidade antes dos analytics por posto;
- contrato dos CSVs com PostgreSQL;
- validação de tipos e limites dos CSVs agregados antes do COPY;
- integridade referencial dos CSVs agregados antes da conexão com PostgreSQL;
- bloqueio pré-carga de dimensões temporais fora de 2026;
- alinhamento automático entre cabeçalhos gerados pelo modelo por posto, contrato da carga e colunas declaradas no SQL;
- alinhamento automático entre o modelo agregado, contrato da carga e `sql/schema.sql`;
- limites de texto, hash SHA-256, coerência temporal e precisão decimal antes do COPY;
- integridade referencial dos CSVs por posto antes da conexão com PostgreSQL;
- unicidade do grão das duas tabelas fato no PostgreSQL;
- unicidade natural de localidade e produto por posto no PostgreSQL;
- separação segura de comandos SQL com strings, comentários e blocos PostgreSQL;
- consistência das consultas SQL agregadas com a última semana por produto e unidade de medida;
- guardas DAX contra mistura de unidades;
- última semana comparável para etanol e gasolina comum;
- consistência das consultas SQL por posto com a regra de última coleta por combinação de produto e unidade de medida;
- regra mínima de amostra por bandeira no SQL;
- geração de gráficos;
- publicação transacional do bundle visual com rollback;
- geração de placeholders visuais para recortes vazios ou sem gasolina comum;
- publicação transacional de snapshot, site e README;
- rollback integral do snapshot versionável quando a instalação falha;
- construção do relatório web;
- proibição de substituição silenciosa da gasolina comum por outro produto no site;
- regra de estilo que bloqueia travessões tipográficos nos arquivos textuais do repositório.

## Integração offline

`tests/integration/test_offline_pipeline.py` cria arquivos temporários sintéticos apenas durante o teste.

O teste percorre:

```text
Excel agregado
  -> transformação
  -> consolidação
  -> qualidade
  -> modelo estrela
  -> analytics

CSV no schema por posto
  -> ingestão
  -> auditoria
  -> qualidade
  -> modelo estrela
  -> analytics por posto

saídas analíticas
  -> cinco gráficos
  -> relatório de insights
```

As fixtures não entram em `data/`, não são publicadas e não são usadas nos resultados do projeto. O objetivo é validar a integração entre componentes sem depender da rede ou da disponibilidade momentânea do portal da ANP.
