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

A carga:

1. valida a existência de todos os CSVs do modelo;
2. cria as estruturas SQL;
3. limpa a carga anterior de forma transacional;
4. carrega dimensões e fatos por `COPY`;
5. cria as views;
6. confere a quantidade de registros nas duas fatos;
7. confirma a transação somente após a validação.

## Tabelas principais

### Agregados oficiais

- `dim_data`
- `dim_produto`
- `dim_localidade`
- `fato_precos_semanais`

### Preços por estabelecimento

- `dim_data_coleta`
- `dim_produto_posto`
- `dim_posto`
- `fato_precos_postos`

## Power BI

No Power BI Desktop:

1. **Obter dados**;
2. **Banco de dados PostgreSQL**;
3. servidor: `localhost:5432`;
4. banco: `combustiveis`;
5. autenticar com as credenciais definidas no ambiente local.

Para a visão agregada, a view `vw_precos_semanais` já entrega dimensões e métricas unidas para exploração rápida. Para um modelo Power BI mais robusto, prefira carregar dimensões e fato separadamente e manter os relacionamentos 1:*.
