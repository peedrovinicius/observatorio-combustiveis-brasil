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
- presença da `posto_chave` determinística na dimensão de estabelecimentos.

Depois disso, a carga:

1. cria ou atualiza as estruturas SQL;
2. limpa a carga anterior de forma transacional;
3. aplica as restrições finais da dimensão de postos e dos grãos das tabelas fato;
4. carrega dimensões e fatos por `COPY`;
5. cria as views;
6. confere a quantidade de registros nas duas fatos;
7. confirma a transação somente após a validação.

A evolução de `dim_posto` é compatível com uma base local criada por versões anteriores do projeto. A coluna `posto_chave` é adicionada quando ausente e passa a ser obrigatória depois da limpeza da carga anterior, antes da importação dos novos dados.

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
