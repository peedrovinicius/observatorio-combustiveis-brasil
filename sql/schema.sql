-- PostgreSQL
-- Modelo dimensional da série semanal agregada da ANP.

CREATE TABLE IF NOT EXISTS dim_data (
    data_id BIGINT PRIMARY KEY,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    ano SMALLINT NOT NULL,
    mes SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    semana_iso SMALLINT NOT NULL CHECK (semana_iso BETWEEN 1 AND 53),
    trimestre SMALLINT NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    UNIQUE (data_inicial, data_final)
);

CREATE TABLE IF NOT EXISTS dim_produto (
    produto_id BIGINT PRIMARY KEY,
    produto VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_localidade (
    localidade_id BIGINT PRIMARY KEY,
    nivel_geografico VARCHAR(20) NOT NULL
        CHECK (nivel_geografico IN ('brasil', 'regiao', 'estado', 'municipio')),
    regiao VARCHAR(40),
    uf CHAR(2),
    estado VARCHAR(120),
    municipio VARCHAR(160)
);

CREATE TABLE IF NOT EXISTS fato_precos_semanais (
    preco_fato_id BIGINT PRIMARY KEY,
    data_id BIGINT NOT NULL REFERENCES dim_data(data_id),
    produto_id BIGINT NOT NULL REFERENCES dim_produto(produto_id),
    localidade_id BIGINT NOT NULL REFERENCES dim_localidade(localidade_id),
    postos_pesquisados INTEGER CHECK (postos_pesquisados >= 0),
    unidade_medida VARCHAR(30),
    preco_medio_revenda NUMERIC(12, 4) NOT NULL
        CHECK (preco_medio_revenda > 0),
    preco_minimo_revenda NUMERIC(12, 4)
        CHECK (preco_minimo_revenda > 0),
    preco_maximo_revenda NUMERIC(12, 4)
        CHECK (preco_maximo_revenda > 0),
    desvio_padrao_revenda NUMERIC(12, 6)
        CHECK (desvio_padrao_revenda >= 0),
    coef_variacao_revenda NUMERIC(12, 6)
        CHECK (coef_variacao_revenda >= 0),
    fonte_arquivo VARCHAR(255),
    fonte_planilha VARCHAR(255),
    CHECK (
        preco_minimo_revenda IS NULL
        OR preco_maximo_revenda IS NULL
        OR preco_minimo_revenda <= preco_maximo_revenda
    ),
    CHECK (
        preco_minimo_revenda IS NULL
        OR preco_medio_revenda >= preco_minimo_revenda
    ),
    CHECK (
        preco_maximo_revenda IS NULL
        OR preco_medio_revenda <= preco_maximo_revenda
    ),
    UNIQUE (data_id, produto_id, localidade_id, unidade_medida)
);

CREATE INDEX IF NOT EXISTS idx_fato_precos_data
    ON fato_precos_semanais(data_id);

CREATE INDEX IF NOT EXISTS idx_fato_precos_produto
    ON fato_precos_semanais(produto_id);

CREATE INDEX IF NOT EXISTS idx_fato_precos_localidade
    ON fato_precos_semanais(localidade_id);

CREATE INDEX IF NOT EXISTS idx_localidade_nivel_uf_municipio
    ON dim_localidade(nivel_geografico, uf, municipio);
