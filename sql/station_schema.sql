-- PostgreSQL
-- Modelo dimensional para observações individuais de preço por posto.

CREATE TABLE IF NOT EXISTS dim_data_coleta (
    data_coleta_id BIGINT PRIMARY KEY,
    data_coleta DATE NOT NULL UNIQUE,
    ano SMALLINT NOT NULL,
    mes SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    semana_iso SMALLINT NOT NULL CHECK (semana_iso BETWEEN 1 AND 53)
);

CREATE TABLE IF NOT EXISTS dim_produto_posto (
    produto_posto_id BIGINT PRIMARY KEY,
    produto VARCHAR(150) NOT NULL,
    unidade_medida VARCHAR(40),
    UNIQUE (produto, unidade_medida)
);

CREATE TABLE IF NOT EXISTS dim_posto (
    posto_id BIGINT PRIMARY KEY,
    cnpj_revenda VARCHAR(30),
    revenda VARCHAR(255),
    bandeira VARCHAR(180),
    regiao VARCHAR(10),
    uf CHAR(2),
    municipio VARCHAR(160),
    logradouro VARCHAR(255),
    numero VARCHAR(40),
    complemento VARCHAR(255),
    bairro VARCHAR(160),
    cep VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS fato_precos_postos (
    preco_posto_id BIGINT PRIMARY KEY,
    data_coleta_id BIGINT NOT NULL
        REFERENCES dim_data_coleta(data_coleta_id),
    produto_posto_id BIGINT NOT NULL
        REFERENCES dim_produto_posto(produto_posto_id),
    posto_id BIGINT NOT NULL
        REFERENCES dim_posto(posto_id),
    preco_revenda NUMERIC(12, 4) NOT NULL
        CHECK (preco_revenda > 0),
    preco_compra NUMERIC(12, 4),
    fonte_arquivo VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_postos_data
    ON fato_precos_postos(data_coleta_id);

CREATE INDEX IF NOT EXISTS idx_postos_produto
    ON fato_precos_postos(produto_posto_id);

CREATE INDEX IF NOT EXISTS idx_postos_posto
    ON fato_precos_postos(posto_id);

CREATE INDEX IF NOT EXISTS idx_dim_posto_geo
    ON dim_posto(uf, municipio, bandeira);
