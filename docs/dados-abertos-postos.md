# Dados abertos por posto

A segunda camada analítica do projeto usa a Série Histórica de Preços de Combustíveis e de GLP da ANP em formato aberto.

A fonte publica observações de preços coletadas em estabelecimentos e documenta campos como região, UF, município, revenda, CNPJ, endereço, produto, data da coleta, valor de venda, unidade de medida e bandeira.

## Estratégia de 2026

Para evitar arquivos redundantes, o coletor usa:

- 1º semestre de 2026 para combustíveis automotivos;
- arquivos mensais do segundo semestre para diesel/GNV e etanol/gasolina;
- as quatro últimas semanas para cobrir o período mais recente ainda não consolidado nos arquivos mensais.

## Sobreposição entre arquivos

A chave natural da observação é:

```text
data da coleta × posto × produto × unidade de medida
```

O preço é uma medida e não faz parte da identidade da observação.

Quando o mesmo registro aparece em mais de uma publicação, o pipeline mantém uma única linha. A janela de quatro últimas semanas tem precedência sobre o arquivo mensal correspondente, permitindo que uma republicação mais recente substitua um valor anterior.

A coluna `fonte_arquivo` preserva o caminho relativo dentro de `data/raw/open_data/`. Para arquivos extraídos de ZIP, isso mantém também o diretório lógico da publicação, por exemplo:

```text
etanol_gasolina_agosto_2026/dados.csv
etanol_gasolina_ultimas_4_semanas/dados.csv
```

Essa referência evita perder a origem quando ZIPs diferentes contêm CSVs com o mesmo nome e permite aplicar a precedência de forma determinística.

Se o CNPJ estiver disponível e possuir estrutura válida, ele identifica o posto. O projeto aceita tanto o formato numérico tradicional quanto o CNPJ alfanumérico de 14 posições, preservando letras na identidade técnica.

Quando o CNPJ estiver ausente, é usado um identificador de fallback composto por UF, município, revenda, logradouro e número. Para que esse fallback seja considerado confiável, revenda, logradouro e número precisam estar preenchidos. Linhas com fallback incompleto não são deduplicadas entre si e são bloqueadas pela validação de qualidade antes da modelagem.

## Grão

A tabela fato por posto representa:

```text
data da coleta × posto × produto × unidade de medida
```

O preço observado é uma medida da fato.

Esse grão é diferente da série agregada oficial. Por isso, as duas fontes não são misturadas na mesma tabela fato.

## Modelo

A camada gera:

- `dim_data_coleta`;
- `dim_produto_posto`;
- `dim_posto`;
- `fato_precos_postos`.

Os arquivos locais são salvos em `data/processed/model_postos` e permanecem fora do Git.

## Uso analítico

Essa camada permite:

- distribuição de preços;
- mediana;
- desvio padrão;
- diferença entre postos;
- comparação por bandeira;
- comparação municipal;
- identificação dos menores e maiores preços observados;
- análise de cobertura da pesquisa.

Os agregados nacionais, regionais e estaduais oficiais continuam sendo preservados na tabela fato agregada, pois possuem metodologia própria de ponderação.


## Integridade da identidade do posto

A auditoria de ingestão registra separadamente:

- CNPJs com estrutura inválida;
- fallbacks incompletos;
- fallbacks sem revenda;
- fallbacks sem logradouro;
- fallbacks sem número.

Registros com fallback incompleto permanecem separados na consolidação e não participam da contagem de sobreposições, pois não existe identidade suficiente para concluir que duas linhas representam o mesmo estabelecimento.

A validação de qualidade posterior trata CNPJ inválido e fallback incompleto como problemas bloqueantes antes da modelagem.

Os CSVs da camada por posto são lidos inicialmente como texto. Isso preserva zeros à esquerda em identificadores como CNPJ e CEP antes das conversões específicas de data e preço.
