# Dicionário de dados

Este dicionário será atualizado conforme os schemas reais das planilhas da ANP forem processados.

## Campos normalizados

| Campo | Descrição |
| --- | --- |
| `data_inicial` | Data inicial do período de pesquisa |
| `data_final` | Data final do período de pesquisa |
| `data_coleta` | Data da coleta no estabelecimento, quando disponível |
| `regiao` | Região geográfica |
| `uf` | Sigla da unidade da Federação |
| `estado` | Nome da unidade da Federação, quando publicado |
| `municipio` | Município pesquisado |
| `produto` | Combustível ou produto pesquisado |
| `postos_pesquisados` | Quantidade de postos pesquisados no recorte agregado |
| `unidade_medida` | Unidade utilizada pela ANP |
| `preco_medio_revenda` | Preço médio de revenda no recorte agregado |
| `preco_minimo_revenda` | Menor preço de revenda no recorte, quando publicado |
| `preco_maximo_revenda` | Maior preço de revenda no recorte, quando publicado |
| `desvio_padrao_revenda` | Desvio padrão dos preços de revenda, quando publicado |
| `coef_variacao_revenda` | Coeficiente de variação, quando publicado |
| `razao_social` | Identificação textual do revendedor, quando disponível |
| `cnpj_revenda` | CNPJ do revendedor, quando disponível |
| `logradouro` | Logradouro do estabelecimento, quando disponível |
| `numero` | Número do endereço, quando disponível |
| `bairro` | Bairro, quando disponível |
| `cep` | CEP, quando disponível |
| `preco_revenda` | Preço observado no posto revendedor |
| `preco_compra` | Preço de compra, se presente na fonte |
| `bandeira` | Bandeira do estabelecimento |
| `fonte_arquivo` | Arquivo bruto que originou o registro |
| `fonte_planilha` | Aba da planilha que originou o registro |

## Regra de compatibilidade

O pipeline não elimina automaticamente colunas não reconhecidas. Campos adicionais publicados pela ANP são preservados com nomes normalizados, permitindo revisar mudanças de schema antes de incorporá-las formalmente ao modelo analítico.

## Observação metodológica

Na série histórica da ANP, o preço médio municipal é calculado por média aritmética simples. Para níveis estadual, regional e nacional, a metodologia da ANP utiliza ponderação conforme as informações de vendas declaradas pelas distribuidoras. Por isso, o projeto não deve recalcular uma média nacional simplesmente como média das médias municipais e tratá-la como equivalente ao indicador oficial.
