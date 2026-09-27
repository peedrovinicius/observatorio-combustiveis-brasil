# Notebooks

## 01: Análise exploratória

[`01_analise_exploratoria.ipynb`](01_analise_exploratoria.ipynb) apresenta a primeira EDA reproduzível do projeto.

O notebook cobre:

- cobertura e granularidade dos dados;
- evolução semanal no nível Brasil;
- ranking de UFs na última semana;
- relação etanol × gasolina por município;
- cuidados metodológicos para não misturar níveis geográficos.

Para usar o notebook, instale o perfil específico:

```bash
python -m pip install -r requirements-notebook.txt
```

Antes de abrir o notebook, execute:

```bash
python -m src.pipeline
```

Isso gera as tabelas em `data/processed/` utilizadas pela análise.

O notebook não contém resultados digitados manualmente nem outputs persistidos. A lógica de ingestão, transformação, consolidação e validação permanece em `src/`, para que o projeto não dependa de execução manual de células.


## Regras de comparação

As visualizações do notebook preservam a unidade de medida. Séries em R$/L e R$/m³ não compartilham o mesmo eixo de preço. O ranking de gasolina comum também exige uma única combinação de produto e unidade antes de desenhar a figura.
