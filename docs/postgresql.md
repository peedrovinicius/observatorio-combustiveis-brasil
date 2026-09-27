# PostgreSQL local

O projeto pode ser executado apenas com CSVs, mas também possui uma camada PostgreSQL reproduzível.

## 1. Criar o banco

Com Docker instalado:

```bash
docker compose up -d postgres
```

O serviço cria:

- banco: `combustiveis`;
- usuário: `combustiveis`;
- porta local: `5432`.

No fluxo `run_local.ps1 -WithPostgres`, o Docker Compose espera o `healthcheck` do PostgreSQL ficar saudável antes de executar `src.load_postgres`. O limite de espera é de 60 segundos.

A senha do `docker-compose.yml` é apenas para desenvolvimento local.

## 2. Configuração

Copie:

```text
.env.example -> .env
```

O padrão é:

```text
DATABASE_URL=postgresql://combustiveis:combustiveis@localhost:5432/combustiveis
```

O arquivo `.env` não é versionado.

## 3. Gerar os dados

```bash
python -m src.pipeline
```

## 4. Carregar o PostgreSQL

```bash
python -m src.load_postgres
```

Antes de abrir a conexão, a carga valida:

- existência de todos os CSVs;
- cabeçalhos duplicados;
- colunas desconhecidas;
- colunas obrigatórias de cada tabela;
- compatibilidade entre os arquivos gerados e o schema PostgreSQL;
- proveniência obrigatória (`fonte_arquivo` e `fonte_planilha`) na fato agregada;
- presença da `posto_chave` determinística na dimensão de estabelecimentos;
- presença de UF, município e proveniência nos registros por posto;
- limites de texto compatíveis com `VARCHAR` e `CHAR`;
- formato da chave SHA-256 de estabelecimento;
- coerência entre `data_coleta`, ano, mês e semana ISO;
- precisão dos preços antes do `NUMERIC(12, 4)`, sem arredondamento silencioso;
- unicidade dos IDs e das chaves naturais nas dimensões por posto;
- existência das chaves estrangeiras usadas pela fato;
- unicidade do grão `data_coleta_id + produto_posto_id + posto_id` antes do `COPY`;
- limites de texto, datas dimensionais e precisão decimal também na camada agregada;
- integridade referencial e unicidade do grão da fato agregada antes do `COPY`;
- permanência das duas dimensões temporais no recorte de 2026.

As verificações de valor acontecem antes de abrir a conexão com o PostgreSQL. Assim, um CSV incompatível falha com a tabela, a linha e a coluna responsáveis pelo problema, sem iniciar a limpeza da carga anterior.

Depois disso, a carga:

1. cria ou atualiza as estruturas SQL;
2. limpa a carga anterior de forma transacional;
3. aplica as restrições finais das dimensões naturais e dos grãos das tabelas fato;
4. carrega dimensões e fatos por `COPY`;
5. cria as views;
6. confere a quantidade de registros nas duas fatos;
7. confirma a transação somente após a validação.

A evolução de `dim_posto` é compatível com uma base local criada por versões anteriores do projeto. A coluna `posto_chave` é adicionada quando ausente. Depois da limpeza da carga anterior, ela passa a ser obrigatória e recebe o índice único antes da importação dos novos dados. Assim, duplicidades legadas não bloqueiam a própria migração.

## Integridade da dimensão de postos

`dim_posto` possui:

- `posto_id` como chave substituta usada pela tabela fato;
- `posto_chave` como chave técnica determinística de 64 caracteres;
- restrição de unicidade para `posto_chave`;
- atributos cadastrais mais recentes observados para cada identidade.

A chave técnica é derivada da identidade do estabelecimento e permite que o PostgreSQL também impeça duplicação lógica de postos, em vez de depender apenas do processamento em Python.

## Tabelas principais

### Agregados oficiais

- `dim_data`;
- `dim_produto`;
- `dim_localidade`;
- `fato_precos_semanais`.

### Preços por estabelecimento

- `dim_data_coleta`;
- `dim_produto_posto`;
- `dim_posto`;
- `fato_precos_postos`.

## Power BI

No Power BI Desktop:

1. **Obter dados**;
2. **Banco de dados PostgreSQL**;
3. servidor: `localhost:5432`;
4. banco: `combustiveis`;
5. autenticar com as credenciais definidas no ambiente local.

Para a visão agregada, a view `vw_precos_semanais` já entrega dimensões e métricas unidas para exploração rápida.

Para um modelo Power BI mais robusto, prefira carregar dimensões e fato separadamente e manter os relacionamentos 1:*.


## Integridade das tabelas fato

A carga cria índices únicos de grão depois do `TRUNCATE` e antes do `COPY`.

Isso serve a dois objetivos:

- proteger novas cargas contra duplicações lógicas;
- atualizar bancos locais criados por versões anteriores sem tentar criar o índice sobre dados legados antes da limpeza.

Os grãos protegidos são:

```text
fato_precos_semanais:
data_id + produto_id + localidade_id + unidade_medida

fato_precos_postos:
data_coleta_id + produto_posto_id + posto_id
```

Na fato agregada, unidade de medida nula é normalizada no índice com `COALESCE`, impedindo duplicidades que uma restrição SQL comum poderia aceitar por tratar valores nulos como distintos.


## Integridade das dimensões

A carga reforça também as chaves naturais das dimensões antes do `COPY`.

`dim_localidade` usa um índice único sobre nível geográfico, região, UF, estado e município, normalizando valores nulos. Isso é necessário porque níveis como Brasil e região possuem naturalmente atributos geográficos não preenchidos.

`dim_produto_posto` exige unidade de medida e usa unicidade lógica por produto e unidade.

Na camada agregada, `fonte_arquivo` e `fonte_planilha` são obrigatórios na fato. A restrição é reaplicada depois do `TRUNCATE` para manter compatibilidade com bancos locais antigos e impedir cargas sem rastreabilidade.

Na camada por posto, `uf`, `municipio` e `fonte_arquivo` também são obrigatórios no PostgreSQL. As três exigências reproduzem o contrato já aplicado pelo pipeline e impedem que uma carga manual crie registros sem geografia mínima ou sem rastreabilidade da origem.

Essas restrições são aplicadas depois do `TRUNCATE`, permitindo atualizar bancos locais antigos sem falhar por duplicidades legadas que serão descartadas pela nova carga.


## Execução dos arquivos SQL

Os arquivos de schema e views são divididos em comandos por um parser local do projeto, sem dependência adicional.

O separador reconhece pontos e vírgulas estruturais e preserva corretamente pontos e vírgulas presentes em:

- strings SQL, incluindo strings de escape do PostgreSQL;
- identificadores entre aspas;
- comentários de linha;
- comentários em bloco, inclusive aninhados;
- blocos PostgreSQL delimitados por `$$` ou `$tag$`.

Isso permite evoluir os scripts com blocos `DO`, funções e textos contendo ponto e vírgula sem quebrar a carga em comandos incompletos.


Se um arquivo terminar com string, identificador, comentário em bloco ou delimitador `$tag$` aberto, a carga falha antes de executar o trecho incompleto.
