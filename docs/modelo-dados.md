# Modelo de dados

## Modelo estrela

```mermaid
erDiagram
    DIM_DATA ||--o{ FATO_PRECOS_SEMANAIS : possui
    DIM_PRODUTO ||--o{ FATO_PRECOS_SEMANAIS : classifica
    DIM_LOCALIDADE ||--o{ FATO_PRECOS_SEMANAIS : localiza

    DIM_DATA {
        bigint data_id PK
        date data_inicial
        date data_final
        smallint ano
        smallint mes
        smallint semana_iso
        smallint trimestre
    }

    DIM_PRODUTO {
        bigint produto_id PK
        varchar produto
    }

    DIM_LOCALIDADE {
        bigint localidade_id PK
        varchar nivel_geografico
        varchar regiao
        char uf
        varchar estado
        varchar municipio
    }

    FATO_PRECOS_SEMANAIS {
        bigint preco_fato_id PK
        bigint data_id FK
        bigint produto_id FK
        bigint localidade_id FK
        integer postos_pesquisados
        numeric preco_medio_revenda
        numeric preco_minimo_revenda
        numeric preco_maximo_revenda
        numeric desvio_padrao_revenda
        numeric coef_variacao_revenda
    }
```

## Grão da fato

Uma linha da `fato_precos_semanais` representa uma observação semanal agregada para a combinação:

**período × produto × localidade × unidade de medida**

O nível geográfico é armazenado na dimensão de localidade e pode ser:

- Brasil;
- região;
- estado;
- município.

## Por que separar dimensões

A modelagem evita repetição de atributos textuais na fato e simplifica relacionamentos no Power BI e consultas SQL.

A mesma estrutura também permite criar filtros consistentes por período, produto e geografia sem duplicar regras em cada visual.

## Dados por posto

Os registros por posto revendedor têm grão diferente dos dados agregados e, por isso, não serão misturados na mesma fato. Quando incorporados, formarão uma segunda tabela fato específica para observações por estabelecimento.
