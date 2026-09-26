# Dados abertos por posto

A segunda camada analítica do projeto usa a Série Histórica de Preços de Combustíveis e de GLP da ANP em formato aberto.

A fonte publica observações de preços coletadas em estabelecimentos e documenta campos como região, UF, município, revenda, CNPJ, endereço, produto, data da coleta, valor de venda, unidade de medida e bandeira.

## Estratégia de 2026

Para evitar arquivos redundantes, o coletor usa:

- 1º semestre de 2026 para combustíveis automotivos;
- arquivos mensais do segundo semestre para diesel/GNV e etanol/gasolina;
- as quatro últimas semanas para cobrir o período mais recente ainda não consolidado nos arquivos mensais.

Sobreposições entre o arquivo mensal e o arquivo das últimas quatro semanas são removidas por chave de negócio.

## Grão

A tabela fato por posto representa:

data da coleta × posto × produto × preço observado

Esse grão é diferente da série agregada oficial. Por isso, as duas fontes não são misturadas na mesma tabela fato.

## Modelo

A camada gera:

- dim_data_coleta;
- dim_produto_posto;
- dim_posto;
- fato_precos_postos.

Os arquivos locais são salvos em data/processed/model_postos e permanecem fora do Git.

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
