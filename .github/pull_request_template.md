## Resumo

Descreva o que foi alterado e por quê.

## Escopo

- [ ] ingestão ou fontes
- [ ] qualidade de dados
- [ ] transformação ou modelo
- [ ] SQL / PostgreSQL
- [ ] análise ou KPI
- [ ] Power BI / visualização
- [ ] documentação
- [ ] testes / CI

## Validação

Informe os comandos executados e o resultado relevante.

```bash
python -m ruff check .
python -m pytest -q --cov=src --cov-report=term-missing
```

## Impacto analítico

Explique se a mudança altera fonte, granularidade, regra de qualidade, KPI, SQL, DAX ou resultado publicado. Se não houver impacto, registre isso explicitamente.

## Checklist

- [ ] a alteração está limitada ao escopo do PR;
- [ ] testes foram adicionados ou atualizados quando necessário;
- [ ] documentação foi atualizada quando o comportamento mudou;
- [ ] dados brutos ou processados não foram versionados;
- [ ] agregados oficiais e dados por posto continuam separados.
