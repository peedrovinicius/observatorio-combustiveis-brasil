-- Modelo dimensional inicial.
-- Os tipos e chaves serão refinados após a inspeção do schema real da ANP.

CREATE TABLE IF NOT EXISTS dim_data (
    data_id INTEGER PRIMARY KEY,
    data_completa DATE NOT NULL UNIQUE,
    ano SMALLINT NOT NULL,
    mes SMALLINT NOT NULL,
    semana SMALLINT,
    trimestre SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_produto (
    produto_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    produto VARCHAR(120) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_localidade (
    localidade_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    regiao VARCHAR(30),
    uf CHAR(2),
    municipio VARCHAR(150)
);

CREATE TABLE IF NOT EXISTS dim_bandeira (
    bandeira_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bandeira VARCHAR(180) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_posto (
    posto_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identificador_fonte VARCHAR(200),
    razao_social VARCHAR(255),
    nome_fantasia VARCHAR(255),
    bandeira_id INTEGER REFERENCES dim_bandeira(bandeira_id),
    localidade_id INTEGER REFERENCES dim_localidade(localidade_id)
);

CREATE TABLE IF NOT EXISTS fato_precos (
    preco_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data_id INTEGER NOT NULL REFERENCES dim_data(data_id),
    produto_id INTEGER NOT NULL REFERENCES dim_produto(produto_id),
    localidade_id INTEGER NOT NULL REFERENCES dim_localidade(localidade_id),
    posto_id INTEGER REFERENCES dim_posto(posto_id),
    preco_revenda NUMERIC(10, 4) NOT NULL CHECK (preco_revenda >= 0),
    unidade_medida VARCHAR(30),
    fonte VARCHAR(120) NOT NULL DEFAULT 'ANP'
);

CREATE INDEX IF NOT EXISTS idx_fato_precos_data ON fato_precos(data_id);
CREATE INDEX IF NOT EXISTS idx_fato_precos_produto ON fato_precos(produto_id);
CREATE INDEX IF NOT EXISTS idx_fato_precos_localidade ON fato_precos(localidade_id);
